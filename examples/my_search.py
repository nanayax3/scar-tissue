#!/usr/bin/env python3
"""
An example for the `command` backend: SQLite full-text search over a table of
memories. Query on stdin, n as the first argument, JSON lines out.

Swap the inside for whatever you actually have. The contract is all that matters.
bm25() is lower-is-better and unbounded, so it's turned into a rough 0-100 here.
Calibrate your floor against what this prints, not against anyone else's numbers.
"""
import json, sqlite3, sys

DB = "/home/me/memories.db"       # CREATE VIRTUAL TABLE mem USING fts5(label, text);

query = sys.stdin.read().strip()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
terms = " OR ".join(w for w in query.replace('"', " ").split() if len(w) > 2)
if terms:
    db = sqlite3.connect(DB)
    for label, text, rank in db.execute(
            "SELECT label, text, bm25(mem) FROM mem WHERE mem MATCH ? ORDER BY bm25(mem) LIMIT ?", (terms, n)):
        print(json.dumps({"label": label, "score": round(100 / (1 + abs(rank)), 1), "text": text}))
