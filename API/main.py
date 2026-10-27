"""Raw Messages API version.

  python API/main.py --scenario scenario.json --out results/api.json
  python API/main.py --chat [--resume]

Needs ANTHROPIC_API_KEY set in the terminal (never in code or git).
"""
import argparse
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from API.agent import ApiBudgetAgent  # noqa: E402
from shared.loc import api_loc  # noqa: E402
from shared.runner import run_scenario  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scenario")
    p.add_argument("--out", default=os.path.join(ROOT, "results", "api.json"))
    p.add_argument("--state-dir", default=os.path.join(ROOT, "state", "api_run"))
    p.add_argument("--chat", action="store_true", help="interactive chat")
    p.add_argument("--resume", action="store_true", help="continue the last conversation")
    a = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY in this terminal first (Claude Console key).")

    if a.chat:
        agent = ApiBudgetAgent(a.state_dir, resume=a.resume)
        while (msg := input("את/ה> ").strip()) not in ("", "exit"):
            print("סוכן>", agent.ask_sync(msg)["response"])
        return

    loc = api_loc(os.path.join(ROOT, "API"))
    asyncio.run(run_scenario(a.scenario, a.out, a.state_dir,
                             lambda d: ApiBudgetAgent(d), "api", loc))


if __name__ == "__main__":
    main()
