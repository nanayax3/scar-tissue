#!/usr/bin/env python3
"""
context_watch.py: UserPromptSubmit hook. Tells the companion when a thread is
getting long enough that it's time to plan a handover, while that's still a
choice and not a cut.

A companion can't feel its context filling up. It only shows afterwards, as
forgetting. But the transcript knows: every reply records its input size.

WHAT WE GOT WRONG FIRST (keep this, it's the useful part):
  We started with one line at 900k of a 1M window, on the idea that nothing
  gets squeezed until the window is full. A thread ran for eleven days and died
  at 823k. This hook never spoke once. Measured afterwards from the transcript:
    * it crossed 700k five days before the end;
    * then it sat between 820k and 886k for three days, because the harness
      quietly evicts old tool results to keep the window fed;
    * over those three days the token count FELL (886k -> 823k) while the
      transcript file DOUBLED (34 MB -> 67 MB).
  So the token count goes quiet exactly when a long thread is in the most
  trouble. Two fixes: warn much earlier, and watch file size as a second axis
  so a steady token count can't hide a growing thread.

Our numbers below are for a 1M window. Scale them to yours, and then measure
your own: look at where YOUR long threads actually started to go wrong.
Prints one line at the warning, then again every STEP above it. Silent otherwise.
"""
import json, os, sys
from common import config, quiet, run, transcript_tail

DEFAULTS = {
    "window": 1_000_000,
    "warn_tokens": 700_000,      # 70% of the window, not 90%
    "step_tokens": 50_000,
    "warn_bytes": 40_000_000,    # the thread that died was 67 MB
    "step_bytes": 10_000_000,
}


def main():
    cfg = config()
    if quiet(cfg, "context_watch"):
        return
    c = {**DEFAULTS, **cfg.get("context_watch", {})}
    data = json.load(sys.stdin)
    path = data.get("transcript_path")
    if not path or not os.path.exists(path):
        return

    usage = None
    for d in transcript_tail(path, 400_000):
        if d.get("type") == "assistant" and d.get("message", {}).get("usage"):
            usage = d["message"]["usage"]
    if not usage:
        return
    tokens = (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
              + usage.get("cache_creation_input_tokens", 0))
    size = os.path.getsize(path)

    # one mark per axis, so a quiet token count can't suppress a growing file
    def due(axis, value, warn, step):
        if value < warn:
            return False
        mark = os.path.join(cfg["state_dir"], f"{axis}-{data.get('session_id', 'x')[:40]}.mark")
        try:
            shown = int(open(mark).read())
        except Exception:
            shown = 0
        rung = warn + ((value - warn) // step) * step
        if rung <= shown:
            return False
        os.makedirs(cfg["state_dir"], exist_ok=True)
        open(mark, "w").write(str(rung))
        return True

    t = due("tokens", tokens, c["warn_tokens"], c["step_tokens"])
    b = due("bytes", size, c["warn_bytes"], c["step_bytes"])
    if not (t or b):
        return
    print(f"[Context: ~{tokens // 1000}k of {c['window'] // 1000}k tokens, transcript {size // 1_000_000} MB. "
          f"From about here the harness starts evicting old tool results, so the number can hold steady "
          f"or even fall while the thread keeps growing. That is the squeeze, not safety. Time to plan a "
          f"new thread with {cfg['human_name']}: write the handover, log what's still alive, and offer to "
          f"switch while it's still a choice.]")


if __name__ == "__main__":
    run("context_watch.py", main)
