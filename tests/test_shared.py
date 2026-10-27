"""Domain logic and checks, no network."""
import pytest

from shared import budget_logic as bl
from shared.checks import run_checks


def test_add_and_balance(state):
    bl.add_expense(40, "'מזון'", "חלב ולחם")
    bl.add_expense(30, "מזון", "פירות")
    out = bl.get_balance("מזון")
    assert "70" in out and "פירות" in out
    assert "מזון: 70" in bl.get_balance("")


def test_bad_amount_raises(state):
    with pytest.raises(bl.ToolError):
        bl.add_expense(-5, "מזון", "x")


def test_exchange_rate_uses_fetcher_and_fallback(state):
    assert "3.6000" in bl.get_exchange_rate("usd", fetcher=lambda c: (3.6, "test"))

    def offline(c):
        raise ConnectionError("no net")
    assert "fallback" in bl.get_exchange_rate("USD", fetcher=offline)
    with pytest.raises(bl.ToolError):
        bl.get_exchange_rate("XYZ", fetcher=offline)


def test_preference_overwrite(state):
    bl.save_preference("food budget", "1500")
    out = bl.save_preference("food_budget", "1200")
    assert "1500" in out
    assert bl.load_memory()["preferences"] == {"food_budget": "1200"}
    assert bl.get_preferences("food_budget") == "food_budget=1200"


def test_checks_read_state(state):
    bl.add_expense(75, "ספרים", "Atomic Habits")
    bl.save_preference("food_budget", "1200 ILS")
    checks = [
        {"name": "a", "type": "expense_count", "value": 1},
        {"name": "b", "type": "expense_match", "category_regex": "ספר", "amount": 75, "description_regex": "atomic"},
        {"name": "c", "type": "preference_match", "key_regex": "food", "value_regex": "1200", "stale_regex": "1500"},
        {"name": "d", "type": "response_matches", "turn": 1, "regex": "atomic"},
    ]
    res = run_checks(checks, [{"turn": 1, "response": "Atomic Habits", "tools": []}])
    assert all(r["pass"] for r in res)
