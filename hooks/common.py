"""
common.py: the bits every hook here shares.

  * config: one JSON file, defaults below, so nothing has a path or a name welded in;
  * fail open, never fail invisible: a hook that crashes stays silent in the
    session (it must never block a message) but leaves a line in a failure log,
    which failures_banner.py reads back at the next session start;
  * "is this a real human message?": headless wakes, subagent hand-backs and
    system notifications also arrive as prompts, and reacting to them is noise.

Config lives at $SCAR_TISSUE_CONFIG, else config.json next to the repo root.
Everything in it is optional.
"""
import datetime, json, os, re, sys, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "human_name": "my human",            # used in the lines the hooks print
    "state_dir": "/tmp/scar-tissue",     # per-session marks; fine to lose on reboot
    "failure_log": os.path.join(ROOT, ".hook-failures.log"),
    "failure_history": os.path.join(ROOT, ".hook-failures.history"),
    # set by whatever spawns a session that ISN'T a conversation with your human
    # (a Discord bridge, a cron wake). Most hooks go quiet when any of these is set.
    "quiet_env": [],
    # prompts that open this way are machines talking, not your human
    "machine_prompts": ["<task-notification", "<system-reminder", "[SYSTEM NOTIFICATION",
                        "Another Claude session"],
    # touch this file to switch off every hook at once
    "kill_switch": os.path.join(ROOT, "OFF"),
}


def config():
    path = os.environ.get("SCAR_TISSUE_CONFIG", os.path.join(ROOT, "config.json"))
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        cfg.update(json.load(open(path)))
    return cfg


def quiet(cfg, name=None):
    """True when this hook should stay out of the way entirely."""
    if os.path.exists(cfg["kill_switch"]):
        return True
    if name and os.path.exists(os.path.join(ROOT, name.upper() + "_OFF")):
        return True
    return any(os.environ.get(v) for v in cfg["quiet_env"])


def is_machine(cfg, prompt):
    return (prompt or "").lstrip().startswith(tuple(cfg["machine_prompts"]))


def transcript_tail(path, nbytes=300_000):
    """Parsed lines from the END of the transcript. It gets big (ours reached 67 MB)."""
    out = []
    if not path or not os.path.exists(path):
        return out
    with open(path, "rb") as f:
        f.seek(max(0, os.path.getsize(path) - nbytes))
        for line in f.read().decode("utf-8", "ignore").splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                continue          # the first line of the tail is usually cut in half
    return out


def text_of(entry):
    c = entry.get("message", {}).get("content")
    if isinstance(c, str):
        return c
    return " \n".join(p.get("text", "") for p in (c or [])
                      if isinstance(p, dict) and p.get("type") == "text")


def strip_actions(text):
    """*curls up next to you* is how someone moves, not what they're talking about."""
    text = re.sub(r"\*[^*]{0,400}\*", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def run(name, main):
    """Run a hook: exit 0 always, and log rather than show any crash."""
    try:
        main()
    except Exception as e:
        try:
            cfg = config()
            with open(cfg["failure_log"], "a") as f:
                f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M} {name}: "
                        f"{type(e).__name__}: {str(e)[:160]}\n")
            if os.environ.get("SCAR_TISSUE_DEBUG"):
                traceback.print_exc()
        except Exception:
            pass
    sys.exit(0)
