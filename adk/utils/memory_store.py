import os, json, time, tempfile
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "monitoring")
JSON_PATH = os.path.join(DATA_DIR, "memory.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

def _append_jsonl(obj: Dict[str, Any]) -> None:
    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    with open(JSON_PATH, "a", encoding="utf-8") as out, open(tmp, "r", encoding="utf-8") as src: out.write(src.read())
    os.remove(tmp)

def write_entry(key: str, value: Any, author: str="agent", tags: Optional[str]=None) -> None:
    _append_jsonl({"action":"write","key":key,"value":value,"author":author,"tags":tags,"ts":int(time.time())})

def read_entry(key: str) -> Optional[Dict[str, Any]]:
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            last = None
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("action")=="write" and obj.get("key")==key:
                        last = {"key": key, "value": obj.get("value"), "author": obj.get("author"), "tags": obj.get("tags"), "updated_at": obj.get("ts")}
                except Exception:
                    continue
            return last
    except FileNotFoundError:
        return None

def list_entries(prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("action")=="write" and obj.get("key","").startswith(prefix):
                        out[obj["key"]] = obj.get("value")
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    return out
