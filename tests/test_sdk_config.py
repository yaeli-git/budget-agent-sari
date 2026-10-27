"""SDK version offline: tool handlers + options. No login or network needed."""
import asyncio
import os

from shared import budget_logic as bl
from SDK import tools
from SDK.agent import SdkBudgetAgent


def run(coro):
    return asyncio.run(coro)


def test_tool_handlers_call_shared_logic(state):
    out = run(tools.add_expense.handler({"amount": 40, "category": "מזון", "description": "חלב"}))
    assert "40" in out["content"][0]["text"] and "is_error" not in out
    assert len(bl.load_memory()["expenses"]) == 1


def test_tool_errors_flagged(state):
    out = run(tools.add_expense.handler({"amount": -3, "category": "מזון", "description": "x"}))
    assert out["is_error"] is True


def test_options_are_restricted(state):
    bl.save_preference("food_budget", "1500")
    agent = SdkBudgetAgent(state)
    o = agent.options
    assert o.strict_mcp_config is True
    assert o.tools == []
    assert o.allowed_tools == [f"mcp__budget__{n}" for n in
                               ("add_expense", "get_balance", "get_exchange_rate", "save_preference", "get_preferences")]
    assert o.setting_sources == ["project"] and o.model == "claude-opus-5-5" and o.effort == "medium"
    assert o.system_prompt.startswith("אתה סוכן פיננסי")
    md = open(os.path.join(o.cwd, "CLAUDE.md"), encoding="utf-8").read()
    assert "food_budget: 1500" in md


def test_replaces_tags_counted():
    from shared.loc import sdk_loc
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    loc = sdk_loc(os.path.join(root, "SDK"))
    assert loc["parts"]["tools"] > 0 and loc["parts"]["loop"] > 0 and loc["parts"]["memory"] > 0
