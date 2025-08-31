from __future__ import annotations

import os
import re
from typing import Dict, List

TEXT_EXTS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".ini",
    ".toml",
    ".html",
    ".xml",
}


def _is_texty(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in TEXT_EXTS


def _iter_repo_files(root: str = "."):
    for dirpath, _, filenames in os.walk(root):
        parts = set(dirpath.split(os.sep))
        if ".git" in parts or ".venv" in parts or "node_modules" in parts:
            continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            if _is_texty(path):
                yield path


def repo_search(pattern: str, flags: str = "i", max_hits: int = 500) -> Dict[str, object]:
    """Search text files in the repo. Returns {'hits': [...], 'truncated': bool}."""
    re_flags = 0
    if "i" in flags:
        re_flags |= re.IGNORECASE
    if "m" in flags:
        re_flags |= re.MULTILINE

    rex = re.compile(pattern, re_flags)
    hits: List[Dict[str, object]] = []

    for path in _iter_repo_files("."):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if rex.search(line):
                        hits.append({"file": path, "line": lineno, "text": line.rstrip()})
                        if len(hits) >= max_hits:
                            return {"hits": hits, "truncated": True}
        except Exception:
            # Ignore unreadable files quietly
            pass

    return {"hits": hits, "truncated": False}
