"""Same budget agent on the Claude Agent SDK: we only configure, Claude Code runs the harness."""
import json
import os

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
                              ResultMessage, TextBlock, ToolUseBlock)

from SDK import tools
from shared import budget_logic
from shared.log import log
from shared.prompts import EFFORT, MODEL, SYSTEM_PROMPT

PRICES = {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}  # Opus 5.5, $/1M


def write_claude_md(workspace: str):
    """Memory: saved preferences -> CLAUDE.md, which Claude Code loads at session start."""
    prefs = budget_logic.load_memory()["preferences"]  # replaces: memory
    lines = ["# זיכרון לטווח ארוך (העדפות שמורות)", ""]  # replaces: memory
    lines += [f"- {k}: {v}" for k, v in prefs.items()] or ["- אין עדיין"]  # replaces: memory
    with open(os.path.join(workspace, "CLAUDE.md"), "w", encoding="utf-8") as f:  # replaces: memory
        f.write("\n".join(lines) + "\n")  # replaces: memory
    log(__file__, f"CLAUDE.md written with {len(prefs)} preferences")


class SdkBudgetAgent:
    def __init__(self, state_dir: str, resume: bool = False):
        budget_logic.set_data_dir(state_dir)
        self.workspace = os.path.join(state_dir, "sdk_workspace")
        os.makedirs(self.workspace, exist_ok=True)
        self.session_file = os.path.join(state_dir, "sdk_session.json")
        resume_id = None
        if resume and os.path.exists(self.session_file):
            with open(self.session_file, encoding="utf-8") as f:
                resume_id = json.load(f)["session_id"]  # replaces: history
        write_claude_md(self.workspace)
        self.options = ClaudeAgentOptions(
            model=MODEL,
            effort=EFFORT,
            thinking={"type": "adaptive"},
            system_prompt=SYSTEM_PROMPT,           # our own prompt instead of Claude Code's
            mcp_servers={tools.SERVER: tools.build_server()},  # replaces: tools
            tools=[],                              # no built-in tools at all
            allowed_tools=tools.TOOL_NAMES,        # replaces: tools
            strict_mcp_config=True,                # ignore any other MCP config on this machine
            setting_sources=["project"],           # replaces: memory, context
            cwd=self.workspace,                    # replaces: memory
            resume=resume_id,                      # replaces: history
            max_turns=10,                          # replaces: loop
        )
        # compaction and caching are automatic inside Claude Code
        # replaces: compaction
        # replaces: caching
        self.client = ClaudeSDKClient(options=self.options)  # replaces: loop
        self._prev: dict = {}  # last cumulative usage per model
        log(__file__, f"options ready (resume={resume_id})")

    async def start(self):
        await self.client.connect()  # replaces: loop

    async def close(self):
        await self.client.disconnect()  # replaces: loop

    async def ask(self, text: str) -> dict:
        await self.client.query(text)  # replaces: loop, history
        reply, used, msg_ids, result = [], [], set(), None
        async for msg in self.client.receive_response():  # replaces: loop
            if isinstance(msg, AssistantMessage):
                msg_ids.add(msg.message_id or id(msg))  # replaces: tokens
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        reply.append(b.text)
                    elif isinstance(b, ToolUseBlock):
                        used.append(b.name.split("__")[-1])
                        log(__file__, f"model called {b.name} {b.input}")
            elif isinstance(msg, ResultMessage):
                result = msg
        return self._record(reply, used, msg_ids, result)

    def _record(self, reply, used, msg_ids, result) -> dict:
        # model_usage and total_cost_usd add up over the session -> take the difference per turn
        mu = (result.model_usage if result else None) or {}  # replaces: tokens
        keys = {"input": "inputTokens", "cache_read": "cacheReadInputTokens",  # replaces: tokens
                "cache_write": "cacheCreationInputTokens", "output": "outputTokens", "cost": "costUSD"}  # replaces: tokens
        per_model = {}
        for model, u in mu.items():  # replaces: tokens
            prev = self._prev.get(model, {})  # replaces: tokens
            per_model[model] = {k: max(0, (u.get(src) or 0) - prev.get(k, 0)) for k, src in keys.items()}  # replaces: tokens
            self._prev[model] = {k: (u.get(src) or 0) for k, src in keys.items()}  # replaces: tokens
        tok = {k: int(sum(m[k] for m in per_model.values())) for k in ("input", "cache_read", "cache_write", "output")}
        sdk_cost = sum(m["cost"] for m in per_model.values())  # replaces: tokens
        cost = sum(tok[k] * PRICES[k] for k in PRICES) / 1e6  # same price table as API/, all models
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump({"session_id": result.session_id if result else None}, f)  # replaces: history
        rec = {"response": (result.result if result and result.result else "\n".join(reply)).strip(),
               "tools": used, "tokens": tok,
               "model_calls": result.num_turns if result else len(msg_ids),  # replaces: tokens
               "cost_usd": round(sdk_cost, 6),
               "cost_usd_at_opus_prices": round(cost, 6),
               "per_model": per_model,
               "sdk_session_total_cost_usd": result.total_cost_usd if result else None}
        log(__file__, f"turn usage {tok} calls={rec['model_calls']} sdk cost ${sdk_cost:.4f} per model "
                      + ", ".join(f"{m}: in+cache={v['input'] + v['cache_read'] + v['cache_write']:.0f} out={v['output']:.0f}"
                                  for m, v in per_model.items()))
        return rec
