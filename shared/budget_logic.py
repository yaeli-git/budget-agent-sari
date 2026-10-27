"""Business logic of the budget agent. Both API/ and SDK/ call these functions.

Everything is saved in one file, budget_memory.json:
  {"expenses": [...], "preferences": {...}}
Tool results are short strings to keep tokens low.
Bad input raises ToolError; each harness passes that back to the model as an error.
"""
import json
import os
from datetime import date

import requests

MEMORY_FILE = os.path.join(os.environ.get("BUDGET_DATA_DIR", "."), "budget_memory.json")

FX_URL = "https://api.frankfurter.app/latest"  # free ECB rates, no key needed
FALLBACK_RATES = {"USD": 3.75, "EUR": 4.10, "GBP": 4.80}  # used only when offline


class ToolError(Exception):
    pass


def set_data_dir(path: str):
    """Point the logic at a state folder (each run starts from a clean one)."""
    global MEMORY_FILE
    os.makedirs(path, exist_ok=True)
    MEMORY_FILE = os.path.join(path, "budget_memory.json")


def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"expenses": [], "preferences": {}}


def save_memory(data: dict):
    tmp = MEMORY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MEMORY_FILE)


def _cat(category: str) -> str:
    c = str(category or "").strip().strip("'\"׳״").strip()
    if not c:
        raise ToolError("category is required")
    return c


def _total(data: dict, category: str) -> float:
    return round(sum(e["amount"] for e in data["expenses"] if e["category"] == category), 2)


def add_expense(amount: float, category: str, description: str) -> str:
    """Add a new expense (amount in ILS)."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ToolError("amount must be a number")
    if amount <= 0:
        raise ToolError("amount must be > 0")
    cat = _cat(category)
    data = load_memory()
    data["expenses"].append({"id": len(data["expenses"]) + 1, "date": date.today().isoformat(),
                             "amount": round(amount, 2), "category": cat,
                             "description": str(description)[:100]})
    save_memory(data)
    return f"נוספה הוצאה #{len(data['expenses'])}: {amount:g}₪ ל-{cat} ({description}). סה\"כ {cat}: {_total(data, cat):g}₪"


def get_balance(category: str = "") -> str:
    """Total spent in one category, with its last items. Empty category = all categories."""
    data = load_memory()
    if not category:
        cats = sorted({e["category"] for e in data["expenses"]})
        if not cats:
            return "אין הוצאות עדיין"
        return "; ".join(f"{c}: {_total(data, c):g}₪" for c in cats)
    cat = _cat(category)
    items = [e for e in data["expenses"] if e["category"] == cat]
    if not items:
        known = sorted({e["category"] for e in data["expenses"]})
        return f"אין הוצאות בקטגוריה {cat}. קטגוריות קיימות: {', '.join(known) or 'אין'}"
    last = ", ".join(f"{e['amount']:g}₪ {e['description']}" for e in items[-5:])
    return f"{cat}: סה\"כ {_total(data, cat):g}₪ ב-{len(items)} הוצאות. אחרונות: {last}"


def _fetch_rate(currency: str) -> tuple[float, str]:
    resp = requests.get(FX_URL, params={"from": currency, "to": "ILS"}, timeout=10)
    resp.raise_for_status()
    body = resp.json()
    return float(body["rates"]["ILS"]), f"ECB {body.get('date')}"


def get_exchange_rate(currency: str, fetcher=_fetch_rate) -> str:
    """External tool: current rate of a foreign currency in ILS (live internet API)."""
    cur = str(currency).strip().upper()
    if len(cur) != 3 or not cur.isalpha():
        raise ToolError("currency must be a 3-letter code like USD")
    if cur == "ILS":
        return "ILS=1₪"
    try:
        rate, source = fetcher(cur)
    except Exception as e:
        if cur not in FALLBACK_RATES:
            raise ToolError(f"no rate for {cur}: {type(e).__name__}")
        rate, source = FALLBACK_RATES[cur], "fallback (offline)"
    return f"1 {cur} = {rate:.4f}₪ ({source})"


def get_preferences(key: str = "") -> str:
    """Long-term memory lookup: one key, or all saved preferences."""
    prefs = load_memory()["preferences"]
    if key:
        k = "_".join(str(key).strip().lower().split())
        return f"{k}={prefs[k]}" if k in prefs else f"אין {k}. מפתחות: {', '.join(prefs) or 'אין'}"
    return "; ".join(f"{k}={v}" for k, v in prefs.items()) or "אין העדפות שמורות"


def save_preference(key: str, value: str) -> str:
    """Long-term memory: save or overwrite a user preference/fact."""
    k = "_".join(str(key).strip().lower().split())
    if not k or not str(value).strip():
        raise ToolError("key and value are required")
    data = load_memory()
    old = data["preferences"].get(k)
    data["preferences"][k] = str(value).strip()[:200]
    save_memory(data)
    return f"נשמר {k}={value}" + (f" (במקום: {old})" if old else "")
