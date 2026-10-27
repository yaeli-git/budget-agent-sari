"""Builds what goes into each turn.

Fixed for the whole session (and cached): system prompt + tool schemas.
Per turn, at the start of the new user message only:
  - today's date
  - the conversation summary, once, right after a compaction
  - only the preferences relevant to this message (memory.py) + the other keys
The context block is saved in history with the message, so the history stays
append-only and the cached prefix never changes.
"""
from datetime import date

from API.harness import memory
from shared.log import log


def build_user_message(user_text: str, history) -> dict:
    hits, other_keys = memory.relevant(user_text)
    lines = [f"date: {date.today().isoformat()}"]
    if history.summary_pending and history.summary:
        lines.append(f"summary of earlier conversation:\n{history.summary}")
    if hits:
        lines.append("saved preferences: " + "; ".join(f"{k}={v}" for k, v in hits.items()))
    if other_keys:
        lines.append("other saved keys (read with get_preferences if needed): " + ", ".join(other_keys))
    ctx = "<context>\n" + "\n".join(lines) + "\n</context>"
    log(__file__, f"context block ~{len(ctx) // 3} tokens: {ctx!r}"[:300])
    return {"role": "user", "content": [{"type": "text", "text": ctx},
                                        {"type": "text", "text": user_text}]}
