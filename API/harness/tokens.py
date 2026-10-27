"""Token usage and cost for every model call, totaled per turn."""
from shared.log import log

# Claude Opus 5.5, USD per 1M tokens
PRICES = {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}


class TurnMeter:
    def __init__(self):
        self.reset()
        self.last_context = 0  # prompt size of the last call (for compaction)

    def reset(self):
        self.usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
        self.calls = 0

    def add(self, usage, label: str = "loop"):
        u = {
            "input": usage.input_tokens or 0,
            "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            "output": usage.output_tokens or 0,
        }
        for k, v in u.items():
            self.usage[k] += v
        self.calls += 1
        if label == "loop":
            self.last_context = u["input"] + u["cache_read"] + u["cache_write"]
        log(__file__, f"call {self.calls} [{label}] in={u['input']} cache_read={u['cache_read']} "
                      f"cache_write={u['cache_write']} out={u['output']} ${cost(u):.4f}")

    def turn_record(self) -> dict:
        c = cost(self.usage)
        log(__file__, f"turn total {self.usage} calls={self.calls} ${c:.4f}")
        return {"tokens": dict(self.usage), "model_calls": self.calls, "cost_usd": round(c, 6)}


def cost(u: dict) -> float:
    return sum(u[k] * PRICES[k] for k in PRICES) / 1_000_000
