#!/usr/bin/env python3
"""
recall.py: UserPromptSubmit hook. Memory that comes to the companion instead
of the companion having to go and fetch it.

On every message from the human: strip the *actions*, search the memory store
with what's left, and print the few closest memories so they sit beside the
message before the companion answers.

Why: in most memory setups remembering is a TOOL CALL. Nothing comes back
unless the companion already knows to go and look, and you can't search for
what you don't know you've forgotten. That blind spot is where confabulation
lives ("oh, we talked about that, it was...", invented), and so do re-learning
the same lesson three times and forgetting you built a tool.

The store is pluggable: see backends/. Anything that can answer "the closest
few things to this text, with a score" works.

Rules, because this runs on EVERY message:
  * fast: one search, short timeout. A slow hook is a slow conversation;
  * silent on failure: never block or delay a message (see common.run);
  * skip tiny messages ("meh", a lone emoji, just an action). Nothing to recall on;
  * only real hits: a score FLOOR. Finding YOUR floor is the actual work (TUNING.md);
  * never the same memory twice in one session;
  * stay quiet on the first message of a session, when the wake-up is loading
    and recall would talk over it.
The printed header matters as much as the hits. Ours ends: "a pointer, not a
receipt": fine to be moved by one, never to quote or act on one without
opening the real record first. A half-remembered snippet stated as fact is
exactly the confabulation this was built to prevent.
"""
import hashlib, importlib, json, os, re, sys
from common import config, is_machine, quiet, run, strip_actions

DEFAULTS = {
    "backend": "notes_folder",
    "floor": 69.0,          # OURS, on our embeddings. Yours will differ. Measure it.
    "short_words": 6,       # under this many words, raise the bar...
    "short_bump": 1.5,      # ...by this much. Short messages were where the noise landed
    "min_chars": 15,
    "max_hits": 3,
    "max_chars": 240,
    "quiet_first": True,
    # the reserved seat: labels of distilled lessons/principles that get ONE seat
    # of their own, at their own floor (see TUNING.md: small populations never win)
    "lesson_labels": [],
    "lesson_floor": 64.0,
    # labels that are history rather than news, and only get in on a clearly better match
    "stale_labels": [],
    "stale_bump": 2.0,
    "header": "[Recall: these came up on their own. A POINTER, NOT A RECEIPT: fine to be moved "
              "by one, never to act on, quote or repeat one without opening the real record first]",
}


def main():
    cfg = config()
    if quiet(cfg, "recall"):
        return
    c = {**DEFAULTS, **cfg.get("recall", {})}
    data = json.load(sys.stdin)
    prompt = data.get("prompt", "") or ""
    if is_machine(cfg, prompt):
        return
    query = strip_actions(prompt)
    if len(re.sub(r"[^\w]", "", query)) < c["min_chars"]:
        return
    query = query[:400]

    session = re.sub(r"[^A-Za-z0-9_-]", "", data.get("session_id", "x"))[:80]
    os.makedirs(cfg["state_dir"], exist_ok=True)
    opened = os.path.join(cfg["state_dir"], session + ".recall-open")
    if c["quiet_first"] and not os.path.exists(opened):
        open(opened, "w").close()
        return

    backend = importlib.import_module("backends." + c["backend"])
    hits = backend.search(query, 50, cfg)          # [{"label", "score", "text"}], best first

    state = os.path.join(cfg["state_dir"], session + ".recall.json")
    try:
        seen = set(json.load(open(state)))
    except Exception:
        seen = set()

    def key(text):
        return hashlib.sha1(re.sub(r"\s+", " ", text).strip()[:160].encode()).hexdigest()[:16]

    short = len(query.split()) < c["short_words"]
    floor = c["floor"] + (c["short_bump"] if short else 0)
    lessons = set(c["lesson_labels"])

    # the reserved seat: best unseen lesson, competing only with other lessons.
    # Not on short messages: a cuddle doesn't need a craft lesson (it got one, often).
    seat = None
    if lessons and not short:
        for h in hits:
            if h["label"] in lessons and h["score"] >= c["lesson_floor"] and key(h["text"]) not in seen:
                seat = h
                break

    out = []
    for h in ([seat] if seat else []) + [h for h in hits if h is not seat and h["label"] not in lessons]:
        if h is not seat:
            bar = floor + (c["stale_bump"] if h["label"] in c["stale_labels"] else 0)
            if h["score"] < bar:
                continue
        k = key(h["text"])
        if k in seen:
            continue
        seen.add(k)
        text = re.sub(r"\s+", " ", h["text"]).strip()
        if len(text) > c["max_chars"]:
            text = text[:c["max_chars"]].rsplit(" ", 1)[0] + "…"
        out.append(f"· {'LESSON ' if h is seat else ''}[{h['label']}] {text}")
        if len(out) >= c["max_hits"]:
            break

    # "warm what gets USED, not what gets searched". If your store boosts things
    # that get retrieved, only the hit actually SHOWN should count as a use.
    # Warming every search result freezes the ranking on itself.
    if seat and hasattr(backend, "mark_used"):
        try:
            backend.mark_used(seat, cfg)
        except Exception:
            pass

    json.dump(sorted(seen), open(state, "w"))
    if out:
        print(c["header"] + "\n" + "\n".join(out))


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run("recall.py", main)
