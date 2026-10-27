"""Pass/fail checks from scenario.json. Most of them read the saved state on disk."""
import re

from shared.budget_logic import load_memory


def _expenses(data, cat_re):
    return [e for e in data["expenses"] if re.search(cat_re, e["category"], re.I)]


def run_check(check: dict, turns: list) -> dict:
    data = load_memory()
    kind = check["type"]
    ok, detail = False, ""
    if kind == "expense_count":
        n = len(data["expenses"])
        ok, detail = n == check["value"], f"count={n}"
    elif kind == "category_total":
        items = _expenses(data, check["category_regex"])
        total = round(sum(e["amount"] for e in items), 2)
        ok, detail = abs(total - check["value"]) < 0.01, f"total={total} items={items}"
    elif kind == "expense_match":
        items = [e for e in _expenses(data, check["category_regex"])
                 if abs(e["amount"] - check["amount"]) < 0.01
                 and re.search(check["description_regex"], e["description"], re.I)]
        ok, detail = len(items) == 1, f"matching={items}"
    elif kind == "preference_match":
        prefs = {k: v for k, v in data["preferences"].items()
                 if re.search(check["key_regex"], k + " " + v, re.I)}
        has = any(re.search(check["value_regex"], v, re.I) for v in prefs.values())
        stale = any(re.search(check["stale_regex"], v, re.I) for v in prefs.values()) if "stale_regex" in check else False
        ok, detail = has and not stale, f"prefs={prefs}"
    elif kind == "response_matches":
        t = turns[check["turn"] - 1]
        ok = re.search(check["regex"], t["response"], re.I) is not None
        detail = f"turn {check['turn']} regex {check['regex']!r}"
    elif kind == "tool_called":
        used = [n for t in turns if check.get("turn") in (None, t["turn"]) for n in t["tools"]]
        ok, detail = check["tool"] in used, f"tools={used}"
    else:
        detail = f"unknown check type {kind}"
    return {"name": check["name"], "state_based": kind not in ("response_matches", "tool_called"),
            "pass": ok, "detail": detail[:300]}


def run_checks(checks: list, turns: list) -> list:
    return [run_check(c, turns) for c in checks]
