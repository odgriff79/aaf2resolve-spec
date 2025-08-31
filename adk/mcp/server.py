<<<<<<< HEAD
# adk/mcp/server.py  (pseudo; adapt to your MCP framework)
from adk.tools.repo_tools import repo_search

TOOLS = {
    "repo_search": {
        "description": "Search the repository for a regex pattern",
        "parameters": {"pattern": "string", "flags": "string", "max_hits": "number"},
        "handler": lambda args: repo_search(
            pattern=args.get("pattern",""),
            flags=args.get("flags","i"),
            max_hits=int(args.get("max_hits", 500))
        ),
    },
}
=======
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from adk.tools.repo_tools import repo_search
from adk.utils.memory_store import read_entry, write_entry, list_entries

PORT = 4010

class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        tool, args = req.get("tool"), req.get("args", {})
        try:
            if tool == "repo_search":
                result = repo_search(**args)
            elif tool == "memory_read":
                result = read_entry(args.get("key"))
            elif tool == "memory_write":
                write_entry(args["key"], args["value"], author=args.get("author","agent")); result = {"ok": True}
            elif tool == "memory_list":
                result = list_entries(args.get("prefix",""))
            else:
                self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"unknown tool"}'); return
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"result": result}).encode("utf-8"))
        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

def main():
    print(f"ADK MCP server listening on http://0.0.0.0:{PORT} (tools: repo_search, memory_read, memory_write, memory_list)")
    HTTPServer(("0.0.0.0", PORT), MCPHandler).serve_forever()

if __name__ == "__main__":
    main()
>>>>>>> 96048c5 (Add MCP server and tools (repo_search, memory_store, memory read/write/list))
