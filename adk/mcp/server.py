from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from adk.tools.repo_tools import repo_search
from adk.utils.memory_store import list_entries, read_entry, write_entry


class MCPEndpoint(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw) if raw else {}
            tool = data.get("tool")
            args = data.get("args", {}) or {}

            if tool == "memory_read":
                key = args.get("key", "")
                result = read_entry(key)
            elif tool == "memory_write":
                key = args.get("key", "")
                value = args.get("value", {})
                author = args.get("author", "system")
                write_entry(key, value, author=author)
                result = {"ok": True}
            elif tool == "memory_list":
                prefix = args.get("prefix", "")
                result = list_entries(prefix)
            elif tool == "repo_search":
                pattern = args.get("pattern", "")
                flags = args.get("flags", "i")
                max_hits = int(args.get("max_hits", 500))
                result = repo_search(pattern, flags=flags, max_hits=max_hits)
            else:
                self._send_json(400, {"error": "unknown tool", "tool": tool})
                return

            self._send_json(200, {"result": result})
        except Exception as e:
            self._send_json(500, {"error": str(e)})


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8765), MCPEndpoint)
    print("MCP server listening on http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
