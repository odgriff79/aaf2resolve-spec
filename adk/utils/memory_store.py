import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "monitoring"  
DB_PATH = DATA_DIR / "memory.sqlite"

def write_entry(key: str, value: Any, author: str = "agent", tags: str = "") -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ts = int(time.time())
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS entries(
        key TEXT PRIMARY KEY, 
        value TEXT NOT NULL, 
        author TEXT, 
        tags TEXT, 
        updated_at INTEGER NOT NULL
    )""")
    con.execute("INSERT OR REPLACE INTO entries(key,value,author,tags,updated_at) VALUES(?,?,?,?,?)",
                (key, json.dumps(value), author, tags, ts))
    con.close()
    print(f"Memory entry written: {key}")

def read_entry(key: str) -> Optional[Dict[str, Any]]:
    if not DB_PATH.exists():
        return None
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT key, value, author, tags, updated_at FROM entries WHERE key=?", (key,)).fetchone()
    con.close()
    if not row: 
        return None
    k, v, a, t, u = row
    return {"key": k, "value": json.loads(v), "author": a, "tags": t, "updated_at": u}
