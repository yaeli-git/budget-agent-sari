"""Builds the tables of REPORT.md from results/api.json and results/sdk.json.

  python shared/report.py
The analysis text lives in REPORT_TEXT.md (written by hand); the numbers are
filled in here, so nothing in the tables is typed manually.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]


def load(name):
    path = os.path.join(ROOT, "results", f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cell(r, fn):
    return fn(r) if r else "לא הורץ עדיין"


def main():
    api, sdk = load("api"), load("sdk")
    rows = [
        ("טוקנים input (לא מ-cache)", lambda r: f"{r['totals']['input']:,}"),
        ("cache read", lambda r: f"{r['totals']['cache_read']:,}"),
        ("cache write", lambda r: f"{r['totals']['cache_write']:,}"),
        ("output", lambda r: f"{r['totals']['output']:,}"),
        ("אחוז cache (read מתוך כל ה-input)", lambda r: f"{r['totals']['cache_hit_pct']}%"),
        ("קריאות למודל", lambda r: str(r["totals"]["model_calls"])),
        ("קריאות לכלים", lambda r: str(r["totals"]["tool_calls"])),
        ("עלות (USD)", lambda r: f"${r['totals']['cost_usd']:.4f}"),
        ("זמן (שניות)", lambda r: str(r["totals"]["seconds"])),
        ("בדיקות שעברו", lambda r: r["checks_passed"]),
    ]
    out = ["# דוח השוואה: סוכן תקציב אישי והמרת מטבעות (API מול SDK)", "",
           f"מודל: `claude-opus-5-5`, effort: `medium`, אותו system prompt ואותם כלים בשתי הגרסאות. "
           f"כל המספרים נוצרו ע\"י `python shared/report.py` מתוך `results/`.", "",
           "## 1. תוצאות הריצה", "", "| מדד | API | SDK |", "|---|---|---|"]
    out += [f"| {name} | {cell(api, fn)} | {cell(sdk, fn)} |" for name, fn in rows]

    out += ["", "### לפי תור", "", "| תור | סשן | API: in / cache read / cache write / out | API קריאות | API $ "
            "| SDK: in / cache read / cache write / out | SDK קריאות | SDK $ |", "|---|---|---|---|---|---|---|---|"]
    n = len((api or sdk or {"turns": []})["turns"])
    for i in range(n):
        def t(r):
            if not r:
                return ["-", "-", "-"]
            x = r["turns"][i]
            k = x["tokens"]
            return [f"{k['input']:,} / {k['cache_read']:,} / {k['cache_write']:,} / {k['output']:,}",
                    str(x["model_calls"]), f"{x['cost_usd']:.4f}"]
        s = (api or sdk)["turns"][i]["session"]
        out.append(f"| {i + 1} | {s} | " + " | ".join(t(api) + t(sdk)) + " |")

    out += ["", "### בדיקות", "", "| בדיקה | על המצב השמור? | API | SDK |", "|---|---|---|---|"]
    names = (api or sdk)["checks"]
    for i, c in enumerate(names):
        a = ("✅" if api["checks"][i]["pass"] else "❌") if api else "-"
        b = ("✅" if sdk["checks"][i]["pass"] else "❌") if sdk else "-"
        out.append(f"| {c['name']} | {'כן' if c['state_based'] else 'לא'} | {a} | {b} |")

    out += ["", "## 2. שורות קוד לכל חלק ב-harness", "",
            "API: שורות קוד בקובץ `API/harness/<part>.py` (בלי הערות ושורות ריקות). "
            "SDK: מספר השורות שמסומנות `# replaces: <part>`.", "",
            "| חלק | API | SDK |", "|---|---|---|"]
    from shared.loc import api_loc, sdk_loc
    al, sl = api_loc(os.path.join(ROOT, "API")), sdk_loc(os.path.join(ROOT, "SDK"))
    for p in PARTS:
        out.append(f"| {p} | {al['parts'][p]} | {sl['parts'][p]} |")
    out.append(f"| **סה\"כ harness** | **{al['harness_total']}** | **{sl['harness_total']}** |")
    out.append(f"| קוד חיבור (main/agent/tools) | {sum(al['glue'].values())} | {sum(sl['glue'].values())} |")

    with open(os.path.join(ROOT, "REPORT_TEXT.md"), encoding="utf-8") as f:
        out += ["", f.read()]
    with open(os.path.join(ROOT, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("[report.py] wrote REPORT.md")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    main()
