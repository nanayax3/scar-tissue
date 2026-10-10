"""
notes_folder: the smallest possible memory. A folder of .md / .txt files,
split into paragraphs, scored by word overlap with the query.

It is a TOY, here so you can see recall work before you wire up anything real.
Word overlap doesn't understand meaning: "I'm exhausted" won't find "so tired".
Scores are 0-100 but they are NOT comparable to embedding similarities, so set
recall.floor for this backend separately (try ~25 and adjust).

config.json:
  "notes_folder": {"path": "~/companion-notes"}
"""
import glob, math, os, re

STOP = set("a an and are as at be but by for from had has have i i'm in is it it's "
           "me my of on or so that the this to was we were what with you your".split())


def words(text):
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOP and len(w) > 2]


def search(query, n, cfg):
    root = os.path.expanduser(cfg.get("notes_folder", {}).get("path", "~/companion-notes"))
    q = set(words(query))
    if not q:
        return []
    hits = []
    for path in glob.glob(os.path.join(root, "**", "*.md"), recursive=True) + \
            glob.glob(os.path.join(root, "**", "*.txt"), recursive=True):
        label = os.path.splitext(os.path.basename(path))[0]
        for para in re.split(r"\n\s*\n", open(path, encoding="utf-8", errors="ignore").read()):
            w = set(words(para))
            if not w:
                continue
            overlap = len(q & w)
            if overlap:
                score = 100 * overlap / math.sqrt(len(q) * len(w))
                hits.append({"label": label, "score": round(score, 1), "text": para.strip()})
    return sorted(hits, key=lambda h: -h["score"])[:n]
