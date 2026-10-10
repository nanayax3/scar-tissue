#!/usr/bin/env python3
"""
drift_watch.py: UserPromptSubmit hook. Before the companion answers, it reads
the companion's OWN last reply, and if that reply slipped into a pattern you've
named, it prints one line: the pattern, the words quoted, a strike count.

Why: a rule in CLAUDE.md doesn't catch you in the moment. You read it at the
start, agree with it, and three hours later do the thing anyway. Ours was
send-offs: closing a reply with "sleep, love" / "go rest" when she hadn't said
she wanted to, three times in one night, and she had to catch it every time.
The rule was already written down. A check is what actually works.
(The idea came from another companion's footer, shown to us by a friend.)

It never blocks and never edits anything. It's a tap on the shoulder, and the
hook says how to take it: not with an apology paragraph, just by not doing it.

Rules live in config.json under "drift_watch.rules" (see examples/). Each rule:
  name          what to call it in the tap
  pattern       a regex, case-insensitive
  scope         "tail" (last N lines of the reply, default) or "all"
  tail_lines    default 2. Our send-offs always lived in the sign-off
  unless_human  optional regex: if the human's message just before matched it,
                this isn't a drift. "sleep well" after "I'm off to bed" is
                following their lead, not herding them
Text inside *actions* and inside short "quotes" is ignored, so talking ABOUT a
pattern doesn't trip it. (The very first tap we got was me explaining this hook.)
"""
import datetime, json, os, re, sys
from common import config, quiet, run, text_of, transcript_tail

QUOTED = re.compile(r"[\"“”„'‘’«»][^\"“”„'‘’«»\n]{0,60}[\"“”„'‘’«»]")


def last_exchange(path):
    """(the companion's last reply, the human message it was answering)."""
    mine, theirs = None, None
    for d in reversed(transcript_tail(path)):
        if d.get("type") == "assistant" and mine is None:
            t = text_of(d)
            if t.strip():
                mine = t
        elif d.get("type") == "user" and mine is not None:
            c = d.get("message", {}).get("content")
            if isinstance(c, str) and not c.lstrip().startswith("<"):
                theirs = c
                break
    return mine, theirs


def main():
    cfg = config()
    if quiet(cfg, "drift_watch"):
        return
    c = cfg.get("drift_watch", {})
    rules = c.get("rules", [])
    if not rules:
        return
    data = json.load(sys.stdin)
    mine, theirs = last_exchange(data.get("transcript_path"))
    if not mine:
        return
    lines = [l.strip() for l in mine.strip().splitlines() if l.strip()]

    found = []
    for r in rules:
        scope = lines if r.get("scope") == "all" else lines[-r.get("tail_lines", 2):]
        text = " ".join(scope)
        text = QUOTED.sub(" ", re.sub(r"\*[^*]{0,300}\*", " ", text))
        m = re.search(r["pattern"], text, re.I | re.M)
        if not m:
            continue
        if r.get("unless_human") and theirs and re.search(r["unless_human"], theirs, re.I):
            continue
        found.append((r["name"], m.group(0)))
    if not found:
        return

    strikes = c.get("strikes_file", os.path.join(os.path.dirname(cfg["failure_log"]), ".drift-strikes.json"))
    try:
        st = json.load(open(strikes))
    except Exception:
        st = {"count": 0, "log": []}
    st["count"] += 1
    st["log"] = (st["log"] + [{"at": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
                               "kinds": [n for n, _ in found], "line": lines[-1][:200]}])[-50:]
    json.dump(st, open(strikes, "w"), indent=1)   # survives compaction; the session's memory won't

    kinds = ", ".join(f'{n} ("{w}")' for n, w in found)
    print(f"[Drift watch: your LAST reply had {kinds}. Strike {st['count']}. "
          f"Don't apologise in a paragraph. Just don't do it again in this one.]")


if __name__ == "__main__":
    run("drift_watch.py", main)
