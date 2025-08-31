<<<<<<< HEAD
# adk/tools/repo_tools.py
import os, io, re

# Simple allowlist for file types you actually want searched
TEXT_EXTS = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".ini", ".toml", ".html", ".xml"}

def _is_texty(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in TEXT_EXTS

def _iter_repo_files(root="."):
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip obvious junk
        if any(p.startswith(".git") for p in dirpath.split(os.sep)): 
            continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            if _is_texty(path) and os.path.getsize(path) <= 1_000_000:  # <= 1MB
                yield path

def repo_search(pattern: str, flags: str = "i", max_hits: int = 500):
    """
    Search the repo for regex `pattern` (case-insensitive default).
    Returns a list of {file, line, text}.  Limited to texty files and 1MB to be safe.
    """
    re_flags = 0
    if "i" in flags: re_flags |= re.IGNORECASE
    if "m" in flags: re_flags |= re.MULTILINE

    results = []
    rex = re.compile(pattern, re_flags)
=======
import os, io, re
TEXT_EXTS = {".py",".md",".txt",".json",".yml",".yaml",".ini",".toml",".html",".xml"}

def _is_texty(path: str) -> bool:
    _, ext = os.path.splitext(path.lower()); return ext in TEXT_EXTS

def _iter_repo_files(root="."):
    for dirpath, _, filenames in os.walk(root):
        parts = set(dirpath.split(os.sep))
        if ".git" in parts or ".venv" in parts or "node_modules" in parts: continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                if _is_texty(path) and os.path.getsize(path) <= 1_000_000:
                    yield path
            except OSError:
                pass

def repo_search(pattern: str, flags: str = "i", max_hits: int = 500):
    re_flags = 0
    if "i" in flags: re_flags |= re.IGNORECASE
    if "m" in flags: re_flags |= re.MULTILINE
    rex = re.compile(pattern, re_flags)
    hits = []
>>>>>>> 96048c5 (Add MCP server and tools (repo_search, memory_store, memory read/write/list))
    for path in _iter_repo_files("."):
        try:
            with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if rex.search(line):
<<<<<<< HEAD
                        results.append({"file": path, "line": lineno, "text": line.rstrip()})
                        if len(results) >= max_hits:
                            return {"hits": results, "truncated": True}
        except Exception:
            # Ignore unreadable files quietly
            pass
    return {"hits": results, "truncated": False}
=======
                        hits.append({"file": path, "line": lineno, "text": line.rstrip()})
                        if len(hits) >= max_hits:
                            return {"hits": hits, "truncated": True}
        except Exception:
            pass
    return {"hits": hits, "truncated": False}
>>>>>>> 96048c5 (Add MCP server and tools (repo_search, memory_store, memory read/write/list))
