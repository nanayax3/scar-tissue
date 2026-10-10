"""
command: plug in anything. Runs a command of yours, hands it the query on
stdin, and reads JSON lines back: {"label": ..., "score": ..., "text": ...}.

That's the whole contract, so the search can be in any language and talk to
any store: a vector DB, SQLite full-text, a Letta/mem0 API, a script that
greps your journal. Keep it fast. This runs before every reply.

config.json:
  "command": {"run": ["python3", "/home/me/my_search.py"], "timeout": 3}
"""
import json, subprocess


def search(query, n, cfg):
    c = cfg.get("command", {})
    p = subprocess.run(c["run"] + [str(n)], input=query, capture_output=True,
                       text=True, timeout=c.get("timeout", 3), check=True)
    hits = []
    for line in p.stdout.splitlines():
        if line.strip():
            h = json.loads(line)
            hits.append({"label": str(h.get("label", "")), "score": float(h["score"]), "text": h["text"]})
    return sorted(hits, key=lambda h: -h["score"])[:n]
