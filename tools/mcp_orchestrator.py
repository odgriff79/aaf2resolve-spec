#!/usr/bin/env python3
"""
MCP Orchestration Script
Coordinates between internal MCP and GitHub MCP for agent workflows
"""

import requests
import json
import subprocess
import os
from typing import Dict, Any, Optional


class MCPOrchestrator:
    def __init__(self):
        self.internal_mcp_url = "http://127.0.0.1:8765"
        self.github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        
    def call_internal_mcp(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call internal MCP server"""
        response = requests.post(
            self.internal_mcp_url,
            json={"tool": tool, "args": args}
        )
        return response.json()
    
    def call_github_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Call GitHub API directly"""
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        url = f"https://api.github.com/{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        
        return response.json() if response.content else {}
    
    def sync_handoff_with_github(self) -> None:
        """Sync handoff status with GitHub issue"""
        # Read current handoff status
        handoff = self.call_internal_mcp("memory_read", {"key": "current_handoff"})
        
        # Update GitHub issue or create new one
        issue_data = {
            "title": f"Agent Handoff: {handoff.get('owner', 'Unknown')} -> Next",
            "body": f"""
## Current Handoff Status

**Owner**: {handoff.get('owner', 'Unknown')}
**Status**: {handoff.get('status', 'Unknown')}
**Next Action**: {handoff.get('next_action', 'Unknown')}

**Artifacts**:
{self._format_artifacts(handoff.get('artifacts', []))}

Updated automatically by MCP orchestrator.
            """,
            "labels": ["agent:handoff", "automation"]
        }
        
        # Create or update issue
        self.call_github_api("repos/odgriff79/aaf2resolve-spec/issues", "POST", issue_data)
    
    def _format_artifacts(self, artifacts):
        """Format artifacts for GitHub issue"""
        if not artifacts:
            return "None"
        
        formatted = []
        for artifact in artifacts:
            formatted.append(f"- **{artifact.get('path', 'unknown')}** (rev {artifact.get('revision', '?')})")
        
        return "\n".join(formatted)


if __name__ == "__main__":
    orchestrator = MCPOrchestrator()
    orchestrator.sync_handoff_with_github()
    print("✅ Handoff status synced with GitHub")
