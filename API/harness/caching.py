"""Prompt-cache breakpoints (cache_control) for each request.

Render order is tools -> system -> messages. Two breakpoints:
  1. end of the system prompt  -> caches tools + system (same every call)
  2. last block of the last message -> caches the whole history so far, so the
     next call (next tool round or next turn) reads it from cache.
The markers go on a copy; the history on disk never carries them.
"""
import copy

from shared.log import log

EPHEMERAL = {"type": "ephemeral"}


def apply(system_prompt: str, messages: list) -> tuple[list, list]:
    system = [{"type": "text", "text": system_prompt, "cache_control": EPHEMERAL}]
    msgs = copy.deepcopy(messages)
    last = msgs[-1]
    if isinstance(last["content"], str):
        last["content"] = [{"type": "text", "text": last["content"]}]
    # thinking blocks can't carry cache_control; use the last block that can
    for block in reversed(last["content"]):
        if block.get("type") not in ("thinking", "redacted_thinking"):
            block["cache_control"] = EPHEMERAL
            break
    log(__file__, f"breakpoints: system + message #{len(msgs)} ({last['role']})")
    return system, msgs
