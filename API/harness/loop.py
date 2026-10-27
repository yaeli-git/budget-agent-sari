"""The agent loop: call the model while stop_reason == "tool_use".

All tool_results of one assistant message go back in ONE user message.
"""
from API.harness import caching, tools
from shared.log import log
from shared.prompts import EFFORT, MODEL, SYSTEM_PROMPT

MAX_ROUNDS = 10


def _dump(block) -> dict:
    return block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else dict(block)


def run_agent_loop(client, history, meter) -> tuple[str, list]:
    """History must already end with the new user message. Returns (reply text, tools used)."""
    used: list[str] = []
    for rnd in range(1, MAX_ROUNDS + 1):
        system, messages = caching.apply(SYSTEM_PROMPT, history.messages)
        log(__file__, f"round {rnd}: calling {MODEL} with {len(messages)} messages")
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=system,
            tools=tools.BUDGET_TOOLS,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
        )
        meter.add(response.usage)
        content = [_dump(b) for b in response.content]
        history.append({"role": "assistant", "content": content})
        log(__file__, f"stop_reason={response.stop_reason}")

        if response.stop_reason == "tool_use":
            results, names = tools.run_tool_uses(content)
            used += names
            history.append({"role": "user", "content": results})
            continue
        if response.stop_reason == "refusal":
            return "(הבקשה נדחתה על ידי המודל)", used
        text = "".join(b["text"] for b in content if b.get("type") == "text").strip()
        return text, used
    log(__file__, f"stopped after {MAX_ROUNDS} rounds")
    return "(הסוכן עצר: יותר מדי סבבי כלים)", used
