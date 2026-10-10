#!/usr/bin/env python3
"""
standing.py: SessionStart hook. Puts a short block of standing knowledge at
the top of every session: the few most PROVEN things about the human, and
about the companion's own usual ways of going wrong.

Why: recall brings what matches the message. Some things should just be
THERE, without a match: "it was just there, available as knowledge, not
something you have to actively reach for." That's what our human asked for.

Two lessons from building ours:
  * About the human, these DESCRIBE, they don't instruct. "Tends to wind down
    by talking late at night" is a pointer to ask, not a licence to assume.
    The header says so every time.
  * If your store boosts what gets read, read this block WITHOUT boosting it.
    Otherwise the block warms itself every session and nothing new ever
    gets in.

Source is either a file (one item per line, under "## about <human>" and
"## about me" headings) or a command that prints that same format.
config.json:
  "standing": {"file": "~/companion/standing.md"}      or
  "standing": {"run": ["python3", "/home/me/top_principles.py"]}
"""
import os, subprocess
from common import config, quiet, run


def main():
    cfg = config()
    if quiet(cfg, "standing"):
        return
    c = cfg.get("standing", {})
    if c.get("run"):
        text = subprocess.run(c["run"], capture_output=True, text=True, timeout=8, check=True).stdout
    elif c.get("file") and os.path.exists(os.path.expanduser(c["file"])):
        text = open(os.path.expanduser(c["file"])).read()
    else:
        return
    body = [l.rstrip() for l in text.splitlines() if l.strip()]
    if not body:
        return
    print(f"[Standing knowledge: the most proven things. About {cfg['human_name']}, these DESCRIBE, "
          f"never instruct. Pointers, not verdicts: ask, don't assume.]")
    print("\n".join(body[: c.get("max_lines", 14)]))


if __name__ == "__main__":
    run("standing.py", main)
