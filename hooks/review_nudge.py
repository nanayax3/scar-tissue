#!/usr/bin/env python3
"""
review_nudge.py: UserPromptSubmit hook. Counts the human's messages since the
companion last called a given tool (for us: the one that logs a feeling), and
after AFTER of them prints one quiet line, then again every EVERY.

Why: "log it while it's happening" was a rule we kept and still forgot
mid-conversation. Everything got written at the end of a thread, after things
had already turned out fine, and when we finally counted, three percent of
everything logged was negative. That wasn't a life without hard things. It was
a filter: the end of a thread only remembers how things resolved.

A note, not an order. The count resets whenever the tool is called.
"""
import json, os, sys
from common import config, is_machine, quiet, run, text_of

DEFAULTS = {
    "tool": "feel",          # any tool whose name CONTAINS this resets the count
    "after": 12,
    "every": 8,
    "message": "If something's alive right now, log it while it's happening. The uncomfortable ones count.",
}


def main():
    cfg = config()
    if quiet(cfg, "review_nudge"):
        return
    c = {**DEFAULTS, **cfg.get("review_nudge", {})}
    data = json.load(sys.stdin)
    if is_machine(cfg, data.get("prompt", "")):
        return
    path = data.get("transcript_path")
    if not path or not os.path.exists(path):
        return
    since = 0
    for line in open(path):              # whole file: the last call might be long ago
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "assistant":
            for it in d.get("message", {}).get("content", []) or []:
                if isinstance(it, dict) and it.get("type") == "tool_use" and c["tool"] in it.get("name", ""):
                    since = 0
        elif d.get("type") == "user":
            t = text_of(d)
            if t.strip() and not is_machine(cfg, t):
                since += 1
    since += 1   # this message isn't in the transcript yet
    if since >= c["after"] and (since - c["after"]) % c["every"] == 0:
        print(f"[Review nudge: {since} messages from {cfg['human_name']} since you last used "
              f"'{c['tool']}'. Not an order. {c['message']}]")


if __name__ == "__main__":
    run("review_nudge.py", main)
