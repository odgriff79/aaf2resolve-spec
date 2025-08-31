<<<<<<< HEAD
cat > adk/mcp/server.py <<'PY'
=======
>>>>>>> 1addfca (fix(adk): resolve merge markers & semicolon one-liners in MCP server and repo_tools)
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

<<<<<<< HEAD
from adk.utils.memory_store import read_entry, write_entry, list_entries
from adk.tools.repo_tools import repo_search
=======
from adk.tools.repo_tools import repo_search
from adk.utils.memory_store import list_entries, read_entry, write_entry
>>>>>>> 1addfca (fix(adk): resolve merge markers & semicolon one-liners in MCP server and repo_tools)


class MCPEndpoint(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_POST(self) -> None:
        try:
            if self.path != "/tool":
                self._send_json(404, {"error": "not found"})
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8"))

            tool = body.get("tool")
            args: Dict[str, Any] = body.get("args", {}) or {}

            if tool == "memory_read":
                key = str(args.get("key", ""))
                result = read_entry(key)
                self._send_json(200, {"result": result})

            elif tool == "memory_write":
                key = str(args.get("key", ""))
                value = args.get("value", {})
                author = str(args.get("author", "agent"))
                write_entry(key, value, author=author)
                self._send_json(200, {"result": "ok"})

            elif tool == "memory_list":
                prefix = str(args.get("prefix", ""))
                result = list_entries(prefix)
                self._send_json(200, {"result": result})

            elif tool == "repo_search":
                pattern = str(args.get("pattern", ""))
                flags = str(args.get("flags", "i"))
                max_hits = int(args.get("max_hits", 500))
                result = repo_search(pattern, flags=flags, max_hits=max_hits)
                self._send_json(200, {"result": result})

            else:
                self._send_json(400, {"error": "unknown tool", "tool": tool})

        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8765), MCPEndpoint)
    print("MCP server listening on http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
<<<<<<< HEAD
PY
=======
>>>>>>> 1addfca (fix(adk): resolve merge markers & semicolon one-liners in MCP server and repo_tools)
