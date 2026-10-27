"""Conversation history saved to disk as append-only JSONL.

Each line is one event:
  {"kind": "message", "message": {...}}      a user/assistant message
  {"kind": "compaction", "summary": "..."}   everything before this line was summarized
Nothing is ever rewritten. On load, the active conversation is the messages
after the last compaction line (the summary itself is passed in the next user turn).
Keeping the history append-only also keeps Opus 5.5 thinking blocks valid
and the prompt cache warm.
"""
import json
import os

from shared.log import log


class History:
    def __init__(self, path: str):
        self.path = path
        self.messages: list[dict] = []
        self.summary: str | None = None
        self.summary_pending = False  # summary not yet sent to the model
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            self._load()

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                ev = json.loads(line)
                if ev["kind"] == "compaction":
                    self.messages, self.summary, self.summary_pending = [], ev["summary"], True
                else:
                    self.messages.append(ev["message"])
                    self.summary_pending = False
        log(__file__, f"loaded {len(self.messages)} messages from {self.path}"
                      + (" (+summary)" if self.summary else ""))

    def _write(self, ev: dict):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def append(self, message: dict):
        self.messages.append(message)
        self.summary_pending = False
        self._write({"kind": "message", "message": message})
        log(__file__, f"append {message['role']} message #{len(self.messages)}")

    def compact(self, summary: str):
        self._write({"kind": "compaction", "summary": summary})
        self.messages, self.summary, self.summary_pending = [], summary, True
        log(__file__, "compaction marker written; active history reset to summary")
