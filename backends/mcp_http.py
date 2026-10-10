"""
mcp_http: call a search tool on a remote MCP server (streamable HTTP), the same
server the companion already uses as a tool. This is how ours works: the hook
calls the memory server's own search, so recall and a manual search can never
disagree about what's in there.

MCP tools return TEXT, formatted for a model to read, so you have to tell this
backend how to cut that text into hits: a regex matching each hit's header,
with named groups `label` and `score`. Everything between one header and the
next is that hit's text.

config.json:
  "mcp_http": {
    "url": "https://your-memory-server.example/mcp",
    "headers": {"Authorization": "Bearer ..."},       (or put it in an env var, below)
    "auth_env": "MEMORY_TOKEN",                       optional: header from env
    "tool": "search_memories",
    "args": {"query": "{query}", "limit": "{n}"},     {query} and {n} get filled in
    "header_regex": "^\\*\\*\\[(?P<label>.+?)\\]\\*\\* \\((?P<score>[\\d.]+)%\\)$",
    "use_tool": null,          optional: a tool to call on the hit that was SHOWN
    "use_args": {"query": "{text}"}
  }
The example regex matches headers like  **[tender]** (72.0%)
Keep secrets out of config.json if the repo is public: use auth_env.
"""
import json, os, re, urllib.request


def _call(c, tool, args):
    # Name yourself. Cloudflare (and others) answer Python's default User-Agent
    # with a flat 403, which looks exactly like a bad token.
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "User-Agent": "scar-tissue-recall/1"}
    headers.update(c.get("headers", {}))
    if c.get("auth_env") and os.environ.get(c["auth_env"]):
        headers["Authorization"] = "Bearer " + os.environ[c["auth_env"]]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    raw = urllib.request.urlopen(urllib.request.Request(c["url"], body, headers),
                                 timeout=c.get("timeout", 3)).read().decode()
    if raw.lstrip().startswith(("event:", "data:")):   # SSE: the last data line is the answer
        raw = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")][-1]
    return "".join(x.get("text", "") for x in json.loads(raw)["result"]["content"])


def _fill(template, **kw):
    out = {}
    for k, v in template.items():
        if isinstance(v, str) and v.startswith("{") and v.endswith("}") and v[1:-1] in kw:
            out[k] = kw[v[1:-1]]                       # keep the type: n stays an int
        elif isinstance(v, str):
            out[k] = v.format(**kw)
        else:
            out[k] = v
    return out


def search(query, n, cfg):
    c = cfg["mcp_http"]
    text = _call(c, c["tool"], _fill(c["args"], query=query, n=n))
    marks = list(re.finditer(c["header_regex"], text, re.M))
    hits = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        hits.append({"label": m.group("label").strip(), "score": float(m.group("score")),
                     "text": text[m.end():end].strip()})
    return sorted(hits, key=lambda h: -h["score"])[:n]


def mark_used(hit, cfg):
    c = cfg["mcp_http"]
    if c.get("use_tool"):
        _call(c, c["use_tool"], _fill(c.get("use_args", {"query": "{text}"}), text=hit["text"], label=hit["label"]))
