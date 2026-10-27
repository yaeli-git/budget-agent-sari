"""Counts lines of code per harness part (blank lines, comments and docstrings excluded)."""
import os
import re

PARTS = ["loop", "tools", "history", "memory", "context", "compaction", "caching", "tokens"]


def code_lines(path: str) -> list[str]:
    out, in_doc = [], False
    with open(path, encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            if in_doc:
                in_doc = not (s.endswith('"""') or s.endswith("'''"))
                continue
            if s.startswith(('"""', "'''")):
                in_doc = not (len(s) > 3 and s.endswith(s[:3]))
                continue
            if s and not s.startswith("#"):
                out.append(raw)
    return out


def api_loc(api_dir: str) -> dict:
    h = os.path.join(api_dir, "harness")
    parts = {p: len(code_lines(os.path.join(h, p + ".py"))) for p in PARTS}
    glue = {f: len(code_lines(os.path.join(api_dir, f))) for f in ("main.py", "agent.py")}
    return {"parts": parts, "harness_total": sum(parts.values()), "glue": glue}


def sdk_loc(sdk_dir: str) -> dict:
    """A line counts toward part X when it carries '# replaces: X'."""
    parts = {p: 0 for p in PARTS}
    tag = re.compile(r"#\s*replaces:\s*([\w, ]+)")
    glue = {}
    for f in ("main.py", "agent.py", "tools.py"):
        path = os.path.join(sdk_dir, f)
        glue[f] = len(code_lines(path))
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = tag.search(line)
                if m:
                    for p in m.group(1).replace(" ", "").split(","):
                        if p in parts:
                            parts[p] += 1
    return {"parts": parts, "harness_total": sum(parts.values()), "glue": glue}
