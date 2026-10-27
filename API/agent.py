"""Wires the hand-written harness pieces into one agent (raw Messages API)."""
import json
import os
import uuid

from API.harness import compaction, context, loop
from API.harness.history import History
from API.harness.tokens import TurnMeter
from shared import budget_logic
from shared.log import log


class ApiBudgetAgent:
    def __init__(self, state_dir: str, client=None, resume: bool = False):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()  # key comes only from ANTHROPIC_API_KEY
        self.client = client
        budget_logic.set_data_dir(state_dir)
        base = os.path.join(state_dir, "api")
        os.makedirs(base, exist_ok=True)
        session_file = os.path.join(base, "session.json")
        if resume and os.path.exists(session_file):
            with open(session_file, encoding="utf-8") as f:
                conv_id = json.load(f)["conversation_id"]
        else:
            conv_id = uuid.uuid4().hex[:12]
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump({"conversation_id": conv_id}, f)
        log(__file__, f"conversation {conv_id} (resume={resume})")
        self.history = History(os.path.join(base, "history", f"{conv_id}.jsonl"))
        self.meter = TurnMeter()

    async def start(self):
        pass

    async def close(self):
        pass

    async def ask(self, text: str) -> dict:
        return self.ask_sync(text)

    def ask_sync(self, text: str) -> dict:
        self.meter.reset()
        if compaction.should_compact(self.meter.last_context):
            compaction.compact(self.client, self.history, self.meter)
        self.history.append(context.build_user_message(text, self.history))
        reply, used = loop.run_agent_loop(self.client, self.history, self.meter)
        return {"response": reply, "tools": used, **self.meter.turn_record()}
