from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_DIR = Path("adk/monitoring")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "memory.sqlite"

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memories ("
        " key TEXT PRIMARY KEY,"
        " value TEXT NOT NULL,"
        " author TEXT,"
        " updated_at TEXT NOT NULL)"
    )
    return conn

def write_entry(key: str, value: Any, author: str = "human") -> None:
    payload = json.dumps(value, ensure_ascii=False)
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with _conn() as c:
        c.execute(
            "INSERT INTO memories(key,value,author,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, author=excluded.author, updated_at=excluded.updated_at",
            (key, payload, author, ts),
        )

def read_entry(key: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute(
            "SELECT key, value, author, updated_at FROM memories WHERE key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    k, v, a, t = row
    try:
        js = json.loads(v)
    except Exception:
        js = v
    return {"key": k, "value": js, "author": a, "updated_at": t}

def list_entries() -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("SELECT key, updated_at, author FROM memories ORDER BY key").fetchall()
    return [{"key": k, "updated_at": t, "author": a} for (k, t, a) in rows]
