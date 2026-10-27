"""Tiny logger: every runtime action is printed with the file that did it."""
import os
import sys

QUIET = False


def log(file: str, msg: str):
    if QUIET:
        return
    name = os.path.basename(file)
    line = f"[{name}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:  # Windows consoles without UTF-8
        sys.stdout.write(line.encode("ascii", "replace").decode() + "\n")
