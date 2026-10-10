"""
Memory backends for recall.py. A backend is a module with one function:

    search(query: str, n: int, cfg: dict) -> list[dict]

returning up to n hits, best first, each {"label": str, "score": float, "text": str}.
"label" is whatever your store calls the source (an entity, a feeling's
emotion, a file name). "score" is on whatever scale your store uses. The
floor in config.json has to be on that SAME scale, which is why TUNING.md exists.

Optional:  mark_used(hit, cfg)  called for the one hit that was actually shown.

Shipped here:
  notes_folder  a toy: a folder of markdown, word overlap. No setup. Start here
  command       run any command; it gets the query on stdin and prints JSON lines
  mcp_http      call a search tool on an MCP server over HTTP (what we use)
"""
