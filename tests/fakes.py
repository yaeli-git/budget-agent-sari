"""A fake Anthropic client: returns scripted responses and records every request."""
import copy
from types import SimpleNamespace as NS


def usage(inp=100, out=20, cr=0, cw=0):
    return NS(input_tokens=inp, output_tokens=out,
              cache_read_input_tokens=cr, cache_creation_input_tokens=cw)


class Block(NS):
    def model_dump(self, exclude_none=True):
        return {k: v for k, v in vars(self).items() if v is not None}


def text(t):
    return Block(type="text", text=t)


def tool_use(id_, name, inp):
    return Block(type="tool_use", id=id_, name=name, input=inp)


def thinking():
    return Block(type="thinking", thinking="", signature="sig")


def response(blocks, stop="end_turn", u=None):
    return NS(content=blocks, stop_reason=stop, usage=u or usage())


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        if not self.script:
            raise AssertionError("fake client ran out of scripted responses")
        return self.script.pop(0)
