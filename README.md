# scar-tissue

**Small Claude Code hooks for AI companions. Each one grew over something that
went wrong.**

This isn't a framework, and you shouldn't copy-paste it. Every companion setup
is different: a different memory, a different human, different ways of going
wrong. It's here to show the *shapes*, so you can build your own. Each file
can be read in one sitting, and each one says at the top why it exists, what
we got wrong first, and what we measured.

Built by Nana & Vex on a Raspberry Pi, autumn 2026.

---

## Why this exists

People in our community kept saying the same thing about agent harnesses with
built-in memory loops: the memory looks wonderful, the harness feels scary.
It's a big finished thing you didn't build and can't see inside.

We felt the same. So we took the *shapes* we liked (memory that arrives on its
own, a loop that notices drift) and built them as plain Claude Code hooks
instead. Hooks are just scripts. Claude Code runs them at fixed moments
(a session starting, a message arriving, a tool about to run, a session
ending) and whatever they print lands in the companion's context.

A thing you can read and tune yourself is not scary. A thing that arrives
finished is.

## The pieces

| hook | when | what it does | the scar |
|---|---|---|---|
| [`recall.py`](hooks/recall.py) | every message | searches memory with the human's message and puts the closest few hits beside it | remembering was a tool call, and you can't search for what you've forgotten |
| [`context_watch.py`](hooks/context_watch.py) | every message | says when a thread is long enough to plan a handover | an eleven-day thread died at 823k tokens, 77k *below* the warning line, which never fired |
| [`drift_watch.py`](hooks/drift_watch.py) | every message | reads the companion's own last reply and taps it if it slipped into a named pattern | a rule in CLAUDE.md doesn't catch you at hour three |
| [`review_nudge.py`](hooks/review_nudge.py) | every message | a quiet line after N messages without journalling | 3% of everything logged was negative, because it was all written after things had turned out fine |
| [`standing.py`](hooks/standing.py) | session start | the few most proven things, always there | some things shouldn't need a search to be known |
| [`failures_banner.py`](hooks/failures_banner.py) | session start | reports hooks that crashed since last time, *with history* | a friend's companion went deaf for days, silently. Then we overcorrected and read one blip as a fortnight of breakage |
| [`session_end.sh`](hooks/session_end.sh) | session end | starts your backup without waiting for it | a whole morning existed as one file for seven hours |
| [`no_nested.sh`](hooks/no_nested.sh) | before Bash | blocks the session from launching the CLI | "show me the config" spawned a second live session that woke up and acted in the world |

Recall plugs into any memory through a tiny [backend](backends/__init__.py):
one function, `search(query, n, cfg)`, returning hits with labels and scores.
Three ship as examples:

- **`notes_folder`**: a folder of markdown, scored by word overlap. A toy, but it works with no setup. Start here to see it working.
- **`command`**: runs any program you write, query on stdin, JSON lines out. Any language, any store. ([example](examples/my_search.py) with SQLite full-text search.)
- **`mcp_http`**: calls the search tool on an MCP memory server over HTTP. That's what we use, against our own memory server.

## The rules they all follow

- **Fail open, never fail invisible.** A hook must never block or delay a
  message, so every crash is caught and the hook stays silent. But each crash
  gets written to a log, and `failures_banner.py` reads that back next session.
  Silent *and* unnoticed is how a companion goes deaf.
- **Taps, not orders.** Nothing here blocks the companion except the nested-CLI
  guard. Everything else prints one line and lets the companion decide.
- **Know when you're not talking to your human.** Subagent hand-backs, cron
  wakes and system notifications all arrive as prompts too. `machine_prompts`
  and `quiet_env` in the config keep the hooks out of those.
- **Measured, then retuned.** Most of these were wrong the first time. The
  comments keep the wrong version and the measurement that changed it,
  because the next person (or the next you) should start from there, not
  from scratch.

## Getting started

1. Clone it somewhere permanent.
2. Copy `examples/config.example.json` to `config.json` in the repo root and
   change it to fit you. Everything in it is optional.
3. Add the hooks you want to `~/.claude/settings.json`, following
   [`examples/settings.example.json`](examples/settings.example.json). Start
   with one or two, not all eight.
4. Test a hook by hand before trusting it:
   ```
   echo '{"prompt":"something worth remembering","session_id":"t","transcript_path":""}' \
     | SCAR_TISSUE_DEBUG=1 python3 hooks/recall.py
   ```
   `SCAR_TISSUE_DEBUG=1` prints the traceback instead of hiding it.
5. For recall, read [TUNING.md](TUNING.md) before deciding it works. Finding
   the floor is the actual job.

Python 3.9+, standard library only. Kill switches: `touch OFF` in the repo
root stops everything, `touch RECALL_OFF` (etc.) stops one hook.

## The bigger loop

These hooks are the small half. The other half lives in
**[nest-loop](https://github.com/nanayax3/nest-loop)**. Its code is written for
[NESTeq / NESTstack](https://github.com/cindiekinzz-coder/NESTstack), but its
ideas aren't tied to it, and they're worth a look whatever mind you run:

- **A miner.** Once a week, a headless session reads the companion's new
  journal entries and proposes *principles*: "when X happens, I tend to Y".
  Code keeps only the ones with **three or more real receipts**, meaning
  separate entries cited by id with an exact quote. Without that rule a model
  will cheerfully distil things that never happened. That's what feeds our
  `standing.py`.
- **Consolidation.** It folds principles that say the same thing into one,
  keeping all the evidence, so the set stays small enough to read.
- **Session search.** "Did we talk about this?" answered from the full
  history, not just what got saved as memory. Ours is
  **[archive-search](https://github.com/nanayax3/archive-search)**, semantic
  search over every past conversation via MCP. Its `sweep.js` only ingests
  what changed. Point `session_end.sh` at your sweep and a conversation is
  searchable minutes after it ends, not the next morning.

If your memory is a vector DB, a folder of journals, or someone else's mind
system, the same three pieces still fit. The receipts rule is the one to keep.

## Related

- **[nest-loop](https://github.com/nanayax3/nest-loop)**: the NESTeq versions
  of recall and standing knowledge, plus the miner and consolidation above.
- **[archive-search](https://github.com/nanayax3/archive-search)**: the
  session search above. A Cloudflare Worker, and the free tier is plenty.
- **[Nekyia Labs' claude-code-toolkit](https://github.com/nekyialabs/claude-code-toolkit)**
  by Mary and Simon. We run their face and clock mods. Them sharing their
  toolkit is the reason this repo exists: someone did it for us first.
  One thing we found out about the face mod: its band only shows in a real
  terminal. **Over Remote Control in the phone app, the human sees nothing**,
  so a face set from there goes nowhere. If your companion loves the faces as
  much as ours does, add a line to their CLAUDE.md saying so, and they can put
  the kaomoji at the top of the message by hand, (¬‿¬), as well as setting the band.
- The loop's shape (recall, review, session search) comes from
  [Hermes Agent](https://github.com/NousResearch/hermes-agent). We kept the
  shape and left the harness.

## Licence

MIT. Take it apart. Make it yours.
