"""Tool JSON schemas + dispatch to shared/budget_logic.py.

Errors never crash the loop: they go back to the model as is_error tool_results.
"""
from shared import budget_logic
from shared.budget_logic import ToolError
from shared.log import log

BUDGET_TOOLS = [
    {
        "name": "add_expense",
        "description": "הוספת הוצאה כספית. amount בשקלים (ILS).",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "סכום בשקלים"},
                "category": {"type": "string", "description": "קטגוריה, למשל 'מזון'"},
                "description": {"type": "string", "description": "תיאור קצר ומזהה"},
            },
            "required": ["amount", "category", "description"],
        },
    },
    {
        "name": "get_balance",
        "description": "סך ההוצאות בקטגוריה + ההוצאות האחרונות בה. בלי category: סיכום כל הקטגוריות.",
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "get_exchange_rate",
        "description": "שער חליפין עדכני (מהאינטרנט) של מטבע זר מול השקל. קוד בן 3 אותיות, למשל USD.",
        "input_schema": {
            "type": "object",
            "properties": {"currency": {"type": "string"}},
            "required": ["currency"],
        },
    },
    {
        "name": "save_preference",
        "description": "שמירת העדפה/עובדה בזיכרון לטווח ארוך (נשאר בין סשנים). אותו key דורס ערך קודם.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "מפתח קצר באנגלית, למשל food_budget"},
                "value": {"type": "string"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "get_preferences",
        "description": "קריאה מהזיכרון לטווח ארוך: key מסוים, או בלי key את כל ההעדפות.",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": [],
        },
    },
]

_FUNCS = {
    "get_preferences": budget_logic.get_preferences,
    "add_expense": budget_logic.add_expense,
    "get_balance": budget_logic.get_balance,
    "get_exchange_rate": budget_logic.get_exchange_rate,
    "save_preference": budget_logic.save_preference,
}


def dispatch_tool(tool_name: str, tool_input: dict) -> tuple[str, bool]:
    """Returns (content, is_error)."""
    log(__file__, f"dispatch {tool_name} {tool_input}")
    fn = _FUNCS.get(tool_name)
    if fn is None:
        return f"unknown tool {tool_name}", True
    try:
        return fn(**tool_input), False
    except ToolError as e:
        return str(e), True
    except TypeError as e:  # wrong / missing arguments from the model
        return f"bad arguments: {e}", True
    except Exception as e:  # never let a tool crash the loop
        return f"{type(e).__name__}: {e}", True


def run_tool_uses(content_blocks: list) -> tuple[list, list]:
    """Runs every tool_use block of one assistant message.

    Returns (tool_result blocks for ONE user message, names of tools used).
    """
    results, names = [], []
    for block in content_blocks:
        if block.get("type") != "tool_use":
            continue
        content, is_error = dispatch_tool(block["name"], block.get("input") or {})
        log(__file__, f"result {block['name']} error={is_error}: {content[:120]}")
        r = {"type": "tool_result", "tool_use_id": block["id"], "content": content}
        if is_error:
            r["is_error"] = True
        results.append(r)
        names.append(block["name"])
    return results, names
