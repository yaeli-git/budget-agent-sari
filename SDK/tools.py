"""The same 5 tools, declared for the Claude Agent SDK (in-process MCP server).

Errors are returned with is_error=True so the model sees them, like in API/.
"""
from claude_agent_sdk import create_sdk_mcp_server, tool

from shared import budget_logic
from shared.budget_logic import ToolError
from shared.log import log

SERVER = "budget"


def _wrap(fn, **kwargs):  # replaces: tools
    log(__file__, f"{fn.__name__} {kwargs}")  # replaces: tools
    try:  # replaces: tools
        return {"content": [{"type": "text", "text": fn(**kwargs)}]}  # replaces: tools
    except ToolError as e:  # replaces: tools
        return {"content": [{"type": "text", "text": str(e)}], "is_error": True}  # replaces: tools
    except Exception as e:  # replaces: tools
        return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "is_error": True}  # replaces: tools


@tool("add_expense", "הוספת הוצאה כספית. amount בשקלים (ILS).",  # replaces: tools
      {"amount": float, "category": str, "description": str})  # replaces: tools
async def add_expense(args):  # replaces: tools
    return _wrap(budget_logic.add_expense, amount=args.get("amount"),  # replaces: tools
                 category=args.get("category"), description=args.get("description", ""))  # replaces: tools


@tool("get_balance", "סך ההוצאות בקטגוריה + ההוצאות האחרונות בה. category ריק: כל הקטגוריות.",  # replaces: tools
      {"type": "object", "properties": {"category": {"type": "string"}}, "required": []})  # replaces: tools
async def get_balance(args):  # replaces: tools
    return _wrap(budget_logic.get_balance, category=args.get("category", ""))  # replaces: tools


@tool("get_exchange_rate", "שער חליפין עדכני (מהאינטרנט) של מטבע זר מול השקל, למשל USD.",  # replaces: tools
      {"currency": str})  # replaces: tools
async def get_exchange_rate(args):  # replaces: tools
    return _wrap(budget_logic.get_exchange_rate, currency=args.get("currency", ""))  # replaces: tools


@tool("save_preference", "שמירת העדפה/עובדה בזיכרון לטווח ארוך. אותו key דורס ערך קודם. key קצר באנגלית.",  # replaces: tools, memory
      {"key": str, "value": str})  # replaces: tools, memory
async def save_preference(args):  # replaces: tools, memory
    return _wrap(budget_logic.save_preference, key=args.get("key", ""), value=args.get("value", ""))  # replaces: tools, memory


@tool("get_preferences", "קריאה מהזיכרון לטווח ארוך: key מסוים, או ריק לכל ההעדפות.",  # replaces: tools, memory
      {"type": "object", "properties": {"key": {"type": "string"}}, "required": []})  # replaces: tools, memory
async def get_preferences(args):  # replaces: tools, memory
    return _wrap(budget_logic.get_preferences, key=args.get("key", ""))  # replaces: tools, memory


ALL_TOOLS = [add_expense, get_balance, get_exchange_rate, save_preference, get_preferences]
TOOL_NAMES = [f"mcp__{SERVER}__{t.name}" for t in ALL_TOOLS]  # replaces: tools


def build_server():
    return create_sdk_mcp_server(name=SERVER, version="1.0.0", tools=ALL_TOOLS)  # replaces: tools
