"""
In-memory graph session store.

After a CSV import the parsed graph is saved here under a short session ID.
The frontend can later GET /api/graph/{session_id} to retrieve nodes, edges
and the calculation result without re-uploading the file.

Design notes
------------
• Pure in-memory dict — no database dependency, no disk I/O.
• TTL-based expiry: sessions older than SESSION_TTL_SECONDS are evicted
  lazily on every write (or on explicit cleanup calls).
• Not suitable for multi-process deployments (use Redis there).
  For a single-worker FastAPI process this is perfectly sufficient.
"""

import uuid
import time
from typing import Optional, TypedDict


# ── Configuration ─────────────────────────────────────────────────────────────

SESSION_TTL_SECONDS: int = 60 * 60  # 1 hour
MAX_SESSIONS: int = 500             # cap memory usage


# ── Session schema ────────────────────────────────────────────────────────────

class GraphEntry(TypedDict):
    graph_id: str
    created_at: float
    nodes: list[dict]
    edges: list[dict]
    result: dict


# ── Store ─────────────────────────────────────────────────────────────────────

_store: dict[str, GraphEntry] = {}

def save_graph(nodes: list[dict], edges: list[dict], result: dict) -> str:
    graph_id = str(uuid.uuid4())[:12]
    _store[graph_id] = {
        "graph_id": graph_id,
        "created_at": time.time(),
        "nodes": nodes,
        "edges": edges,
        "result": result
    }
    return graph_id

def get_graph(graph_id: str) -> Optional[GraphEntry]:
    return _store.get(graph_id)