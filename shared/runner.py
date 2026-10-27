"""Runs scenario.json against one harness and writes results/<harness>.json.

Each session gets a brand-new agent instance, so session 2 only knows
what was saved to disk (budget_memory.json).
"""
import json
import os
import shutil
import time

from shared import budget_logic
from shared.checks import run_checks
from shared.log import log


def _sum(turns, key):
    return sum(t["tokens"][key] for t in turns)


async def run_scenario(scenario_path: str, out_path: str, state_dir: str,
                       make_agent, harness: str, loc: dict) -> dict:
    with open(scenario_path, encoding="utf-8") as f:
        scenario = json.load(f)

    if os.path.exists(state_dir):  # every run starts from a clean state
        shutil.rmtree(state_dir)
    budget_logic.set_data_dir(state_dir)
    log(__file__, f"clean state dir {state_dir}")

    sessions: dict[int, list] = {}
    for item in scenario["turns"]:
        sessions.setdefault(item["session"], []).append(item["user_input"])

    turns, n = [], 0
    for s_no in sorted(sessions):
        log(__file__, f"=== session {s_no}: new {harness} agent instance ===")
        agent = make_agent(state_dir)
        await agent.start()
        try:
            for user_msg in sessions[s_no]:
                n += 1
                log(__file__, f"--- turn {n} USER: {user_msg}")
                t0 = time.perf_counter()
                rec = await agent.ask(user_msg)
                rec = {"session": s_no, "turn": n, "user": user_msg, **rec,
                       "seconds": round(time.perf_counter() - t0, 2)}
                log(__file__, f"--- turn {n} AGENT: {rec['response']}")
                turns.append(rec)
        finally:
            await agent.close()

    checks = run_checks(scenario["checks"], turns)
    for c in checks:
        log(__file__, f"check {'PASS' if c['pass'] else 'FAIL'}: {c['name']} ({c['detail'][:120]})")

    inp, cr, cw, out = (_sum(turns, k) for k in ("input", "cache_read", "cache_write", "output"))
    all_in = inp + cr + cw
    result = {
        "harness": harness,
        "model": scenario.get("model"),
        "effort": scenario.get("effort"),
        "turns": turns,
        "totals": {
            "input": inp, "cache_read": cr, "cache_write": cw, "output": out,
            "cache_hit_pct": round(100 * cr / all_in, 1) if all_in else 0.0,
            "model_calls": sum(t["model_calls"] for t in turns),
            "tool_calls": sum(len(t["tools"]) for t in turns),
            "cost_usd": round(sum(t["cost_usd"] for t in turns), 4),
            "seconds": round(sum(t["seconds"] for t in turns), 1),
        },
        "checks": checks,
        "checks_passed": f"{sum(c['pass'] for c in checks)}/{len(checks)}",
        "final_state": budget_logic.load_memory(),
        "loc": loc,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(__file__, f"wrote {out_path}: checks {result['checks_passed']}, cost ${result['totals']['cost_usd']}")
    return result
