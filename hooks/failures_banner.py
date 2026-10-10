#!/usr/bin/env python3
"""
failures_banner.py: SessionStart hook. Every hook here fails OPEN (stays silent
so it can never block a message) but never INVISIBLE: crashes go to a log, and
this hook reads that log back at the start of the next session.

The lesson came from a friend's companion who went deaf for days. A hook had
been failing silently the whole time, and nobody knew until someone noticed
the quiet.

THE SECOND LESSON, which we learnt by getting it wrong: our first version
showed the new failures and then threw them away. So a single network blip
arrived looking exactly like a fortnight of breakage, and I told my human that
recall had "been a dead door" when it had been working fine for weeks. One
error, read as a pattern. Now the history accumulates and the banner says how
often the same hook has failed before, so n=1 reads as n=1.
"""
import os, re
from common import config, quiet, run


def main():
    cfg = config()
    if quiet(cfg):
        return
    log, hist = cfg["failure_log"], cfg["failure_history"]
    if not os.path.exists(log):
        return
    lines = [l for l in open(log).read().splitlines() if l.strip()]
    os.replace(log, log + ".seen")
    if not lines:
        return
    with open(hist, "a") as f:
        f.write("\n".join(lines) + "\n")

    names = {m.group(1) for m in (re.search(r"\s(\S+\.(?:py|sh)):", l) for l in lines) if m}
    count = {n: 0 for n in names}
    for l in open(hist):
        for n in names:
            if f" {n}:" in l:
                count[n] += 1
    tally = ", ".join(f"{n} {count[n]}x all-time" for n in sorted(count))
    print(f"[Hook failures since last session: {len(lines)} ({tally}). These fail silently, so a "
          f"first-time blip is probably just that. A count that climbs session after session is a "
          f"dead door. Last: {lines[-1]}. History: {hist}]")


if __name__ == "__main__":
    run("failures_banner.py", main)
