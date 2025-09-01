#!/usr/bin/env python3
"""
MCP Status Monitor - Real-time multi-agent coordination tracking
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any


def get_internal_mcp_status() -> Dict[str, Any]:
    """Get status from internal MCP server"""
    try:
        response = requests.post(
            "http://127.0.0.1:8765",
            json={"tool": "memory_read", "args": {"key": "handoff_status"}},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json().get("result")
            return result if result is not None else {"error": "No handoff status found"}
        return {"error": "MCP server not responding"}
    except Exception as e:
        return {"error": f"Connection failed: {e}"}


def display_mcp_dashboard():
    """Display comprehensive MCP status dashboard"""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print("🔗 MCP INTEGRATION STATUS DASHBOARD")
    print("=" * 80)
    print(f"⏰ Last Update: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Internal MCP Status
    print("📡 INTERNAL MCP SERVER:")
    internal_status = get_internal_mcp_status()
    
    if "error" in internal_status:
        print(f"   ❌ {internal_status['error']}")
    else:
        handoff = internal_status.get("value", {})
        owner = handoff.get("owner", "Unknown")
        status = handoff.get("status", "Unknown") 
        phase = handoff.get("phase", "Unknown")
        infra_health = handoff.get("infrastructure_health", "Unknown")
        
        print(f"   ✅ Connected | Owner: {owner} | Status: {status}")
        print(f"   📋 Phase: {phase} | Infrastructure: {infra_health}")
    print()
    
    print("🎮 CONTROLS:")
    print("   Ctrl+C to exit | Updates every 15 seconds")
    print("   Internal MCP: http://127.0.0.1:8765")
    print("=" * 80)


def main():
    """Main monitoring loop"""
    print("🚀 Starting MCP Integration Monitor...")
    time.sleep(2)
    
    try:
        while True:
            display_mcp_dashboard()
            time.sleep(15)
    except KeyboardInterrupt:
        print("\n\n👋 MCP Monitor stopped.")


if __name__ == "__main__":
    main()
