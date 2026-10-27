"""API harness tested offline with a fake client (no API key needed)."""
import json
import os

from API.agent import ApiBudgetAgent
from API.harness import caching, compaction, memory, tools
from API.harness.history import History
from shared import budget_logic as bl
from tests.fakes import FakeClient, response, text, thinking, tool_use, usage


def test_loop_runs_tools_and_returns_all_results_in_one_message(state):
    client = FakeClient([
        response([thinking(), tool_use("t1", "add_expense", {"amount": 40, "category": "מזון", "description": "חלב"}),
                  tool_use("t2", "get_balance", {"category": "מזון"})], stop="tool_use"),
        response([thinking(), text("נוסף. סה\"כ 40")]),
    ])
    agent = ApiBudgetAgent(state, client=client)
    rec = agent.ask_sync("קניתי חלב ב-40")
    assert rec["response"] == 'נוסף. סה"כ 40'
    assert rec["tools"] == ["add_expense", "get_balance"] and rec["model_calls"] == 2
    second = client.requests[1]["messages"]
    results = second[-1]["content"]  # one user message, two tool_results
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]
    assert len(bl.load_memory()["expenses"]) == 1
    assert client.requests[0]["output_config"] == {"effort": "medium"}
    assert client.requests[0]["model"] == "claude-opus-5-5"


def test_tool_error_goes_back_as_is_error(state):
    content, err = tools.dispatch_tool("add_expense", {"amount": -1, "category": "x", "description": "y"})
    assert err and "amount" in content
    content, err = tools.dispatch_tool("nope", {})
    assert err
    content, err = tools.dispatch_tool("get_balance", {"wrong_arg": 1})
    assert err and "bad arguments" in content


def test_history_is_append_only_and_reloads(state, tmp_path):
    path = os.path.join(state, "h.jsonl")
    h = History(path)
    h.append({"role": "user", "content": "a"})
    h.append({"role": "assistant", "content": [{"type": "text", "text": "b"}]})
    h.compact("summary")
    h.append({"role": "user", "content": "c"})
    lines = open(path, encoding="utf-8").read().splitlines()
    assert [json.loads(x)["kind"] for x in lines] == ["message", "message", "compaction", "message"]
    h2 = History(path)
    assert h2.summary == "summary" and [m["content"] for m in h2.messages] == ["c"]


def test_resume_loads_previous_conversation(state):
    client = FakeClient([response([text("one")]), response([text("two")])])
    ApiBudgetAgent(state, client=client).ask_sync("hi")
    agent2 = ApiBudgetAgent(state, client=client, resume=True)
    assert len(agent2.history.messages) == 2
    agent2.ask_sync("again")
    assert len(client.requests[1]["messages"]) == 3


def test_caching_marks_system_and_last_block_without_touching_history():
    msgs = [{"role": "user", "content": [{"type": "text", "text": "x"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "y"}, {"type": "thinking", "thinking": "", "signature": "s"}]}]
    system, out = caching.apply("sys", msgs)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert out[-1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in out[-1]["content"][1]
    assert "cache_control" not in msgs[-1]["content"][0]  # original untouched


def test_prefix_is_stable_across_turns(state):
    """Request N+1 must start with exactly the messages of request N (cache + thinking)."""
    client = FakeClient([response([thinking(), text("a")]), response([thinking(), text("b")])])
    agent = ApiBudgetAgent(state, client=client)
    agent.ask_sync("1")
    agent.ask_sync("2")
    strip = lambda ms: json.dumps([{**m, "content": [{k: v for k, v in b.items() if k != "cache_control"} for b in m["content"]]} for m in ms])
    first, second = client.requests[0]["messages"], client.requests[1]["messages"]
    assert strip(second[:len(first)]) == strip(first)
    assert client.requests[0]["system"] == client.requests[1]["system"]


def test_memory_injects_only_relevant_prefs(state):
    bl.save_preference("food_budget", "1500")
    bl.save_preference("trip_goal", "Japan")
    hits, rest = memory.relevant("כמה נשאר לי מהתקציב למזון?")
    assert "food_budget" in hits and "trip_goal" not in hits and rest == ["trip_goal"]


def test_compaction_summarizes_everything_over_threshold(state, monkeypatch):
    monkeypatch.setattr(compaction, "THRESHOLD", 150)
    client = FakeClient([
        response([text("a")], u=usage(inp=200)),       # turn 1: context 200 > 150
        response([text("- user bought milk")]),          # compaction call
        response([text("b")]),                           # turn 2
    ])
    agent = ApiBudgetAgent(state, client=client)
    agent.ask_sync("first")
    rec = agent.ask_sync("second")
    assert rec["model_calls"] == 2  # compaction + loop
    last = client.requests[2]["messages"]
    assert len(last) == 1  # only summary + new turn, nothing replayed
    assert "user bought milk" in last[0]["content"][0]["text"]


def test_tokens_cost_per_turn(state):
    client = FakeClient([response([text("x")], u=usage(inp=1000, out=500, cr=2000, cw=100))])
    rec = ApiBudgetAgent(state, client=client).ask_sync("hi")
    assert rec["tokens"] == {"input": 1000, "cache_read": 2000, "cache_write": 100, "output": 500}
    assert abs(rec["cost_usd"] - (1000 * 4 + 500 * 20 + 2000 * 0.2 + 100 * 5) / 1e6) < 1e-9


def test_full_scenario_runner_offline(tmp_path):
    """scenario.json end to end through shared/runner.py, with a fake model."""
    import asyncio
    from shared.loc import api_loc
    from shared.runner import run_scenario
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    client = FakeClient([response([text("ok")]) for _ in range(8)])
    out = tmp_path / "api.json"
    res = asyncio.run(run_scenario(os.path.join(root, "scenario.json"), str(out), str(tmp_path / "st"),
                                   lambda d: ApiBudgetAgent(d, client=client), "api",
                                   api_loc(os.path.join(root, "API"))))
    assert len(res["turns"]) == 8 and res["totals"]["model_calls"] == 8
    assert res["loc"]["parts"]["loop"] > 0 and out.exists()
    assert res["checks_passed"].endswith("/8")
