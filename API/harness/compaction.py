"""Context-window management: summarize the whole conversation past a threshold.

Shape ("simple compaction"): the entire active history becomes one summary;
the next request starts with that summary + the new user turn, and replays no
earlier turns or thinking blocks. Keeping only the last few turns verbatim would
break Opus 5.5 thinking-block validation, so we don't do that.
Runs only between turns, never in the middle of a tool round.
"""
import os

from shared.log import log
from shared.prompts import MODEL, SUMMARY_PROMPT

THRESHOLD = int(os.environ.get("COMPACT_THRESHOLD", "8000"))  # prompt tokens


def should_compact(last_context_tokens: int) -> bool:
    return last_context_tokens > THRESHOLD


def _transcript(messages: list) -> str:
    out = []
    for m in messages:
        for b in m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]:
            t = b.get("type")
            if t == "text":
                out.append(f"{m['role']}: {b['text']}")
            elif t == "tool_use":
                out.append(f"tool call {b['name']}({b.get('input')})")
            elif t == "tool_result":
                out.append(f"tool result: {str(b.get('content'))[:300]}")
    return "\n".join(out)


def compact(client, history, meter) -> str:
    log(__file__, f"context {meter.last_context} > {THRESHOLD}: summarizing {len(history.messages)} messages")
    prior = f"previous summary:\n{history.summary}\n\n" if history.summary else ""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"{SUMMARY_PROMPT}\n\n{prior}<transcript>\n"
                                              f"{_transcript(history.messages)}\n</transcript>"}],
    )
    meter.add(resp.usage, label="compaction")
    summary = "".join(b.text for b in resp.content if b.type == "text").strip()
    history.compact(summary)
    meter.last_context = 0
    log(__file__, f"summary ({len(summary)} chars): {summary[:150]}")
    return summary
