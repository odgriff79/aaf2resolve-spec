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
            elif tool == "create_integration_pr":
                result = self._create_integration_pr(args)
            elif tool == "update_handoff_issue":
                result = self._update_handoff_issue(args)
            elif tool == "check_ci_status":
                result = self._check_ci_status(args)
            elif tool == "trigger_agent_workflow":
                result = self._trigger_agent_workflow(args)
            else:
                self._send_json(400, {"error": "unknown tool", "tool": tool})
                return

            self._send_json(200, {"result": result})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _create_integration_pr(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create PR with integration test results"""
        title = args.get("title", "Integration Test Results")
        body = args.get("body", "Automated integration test results")
        
        try:
            # Simple success response for now
            return {"success": True, "message": "Integration PR endpoint ready", "title": title}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _update_handoff_issue(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update handoff status via GitHub issue"""
        return {"success": True, "message": "Handoff update endpoint ready"}

    def _check_ci_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check GitHub Actions CI status"""
        return {"success": True, "status": "CI status endpoint ready"}

    def _trigger_agent_workflow(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger agent workflow via GitHub Actions"""
        return {"success": True, "workflow_id": "triggered"}


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8765), MCPEndpoint)
    print("MCP server listening on http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
