"""Long-term memory: where it lives and how we pull from it.

Stored in: budget_memory.json -> "preferences" (written by the save_preference tool).
Retrieval: before each turn we score every saved preference against the user's
message and inject only the matching values. The keys of the rest are listed
(cheap), so the model knows they exist. Expenses are never injected; the model
fetches them with get_balance.
"""
import re

from shared.budget_logic import load_memory
from shared.log import log

# Hebrew words -> English key fragments the model tends to use
_ALIASES = {
    "מזון": "food", "אוכל": "food", "תקציב": "budget", "מטבע": "currency",
    "דולר": "currency", "שקל": "currency", "סכומים": "currency", "ספר": "book",
    "נשאר": "budget", "חודשי": "monthly",
}


def _words(text: str) -> set[str]:
    words = {w.lower() for w in re.findall(r"[\w֐-׿]+", text) if len(w) > 2}
    for w in list(words):
        for heb, eng in _ALIASES.items():
            if heb in w:
                words.add(eng)
    return words


def relevant(user_text: str, limit: int = 5) -> tuple[dict, list]:
    """Returns (matching preferences, keys of the rest)."""
    prefs = load_memory().get("preferences", {})
    msg = _words(user_text)
    scored = []
    for k, v in prefs.items():
        fact = _words(k.replace("_", " ") + " " + v)
        score = len(msg & fact) + sum(1 for part in k.split("_") if part in msg)
        scored.append((score, k, v))
    scored.sort(reverse=True)
    hits = {k: v for s, k, v in scored[:limit] if s > 0}
    rest = [k for s, k, v in scored if k not in hits]
    log(__file__, f"{len(prefs)} saved prefs; injecting {list(hits)}; keys only: {rest}")
    return hits, rest
