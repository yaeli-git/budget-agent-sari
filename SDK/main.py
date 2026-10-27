"""Claude Agent SDK version. Runs on your Claude Code login (no API key).

  python SDK/main.py --scenario scenario.json --out results/sdk.json
"""
import argparse
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from shared.loc import sdk_loc  # noqa: E402
from shared.runner import run_scenario  # noqa: E402
from SDK.agent import SdkBudgetAgent  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", required=True)
    p.add_argument("--out", default=os.path.join(ROOT, "results", "sdk.json"))
    p.add_argument("--state-dir", default=os.path.join(ROOT, "state", "sdk_run"))
    a = p.parse_args()

    # billing must go to the Claude Code login, not to an API key
    if os.environ.pop("ANTHROPIC_API_KEY", None):
        print("[main.py] ANTHROPIC_API_KEY removed for this process (SDK uses your login)")

    loc = sdk_loc(os.path.join(ROOT, "SDK"))
    asyncio.run(run_scenario(a.scenario, a.out, a.state_dir,
                             lambda d: SdkBudgetAgent(d), "sdk", loc))


if __name__ == "__main__":
    main()
