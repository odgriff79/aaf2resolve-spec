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
