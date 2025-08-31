#!/usr/bin/env python3
"""
Real-time Multi-Agent System Monitor

Run this in your Codespaces terminal to watch the multi-agent handoff system.
Shows current status, recent commits, and file changes in real-time.
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def clear_screen():
    """Clear terminal screen."""
    print("\033[2J\033[H", end="")


def run_cmd(cmd: str) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return "ERROR"


def get_handoff_status() -> Dict[str, Any]:
    """Read current handoff status."""
    handoff_file = Path("handoff/handoff.yml")
    if not handoff_file.exists():
        return {"error": "handoff.yml not found"}

    try:
        import yaml

        with open(handoff_file) as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: parse basic YAML manually
        content = handoff_file.read_text()
        status = {}
        for line in content.split("\n"):
            if line.startswith("owner:"):
                status["owner"] = line.split('"')[1] if '"' in line else line.split(":")[1].strip()
            elif line.startswith("status:"):
                status["status"] = line.split('"')[1] if '"' in line else line.split(":")[1].strip()
            elif line.startswith("next_action:"):
                status["next_action"] = line.split(":", 1)[1].strip()
        return status
    except Exception as e:
        return {"error": f"Failed to parse handoff.yml: {e}"}


def get_recent_commits(count: int = 5) -> list:
    """Get recent commit history."""
    cmd = f"git log --oneline -n {count} --pretty=format:'%h|%an|%ar|%s'"
    output = run_cmd(cmd)
    if output == "ERROR":
        return []

    commits = []
    for line in output.split("\n"):
        if "|" in line:
            hash_part, author, time_ago, message = line.split("|", 3)
            commits.append(
                {"hash": hash_part, "author": author, "time": time_ago, "message": message}
            )
    return commits


def get_repo_status() -> Dict[str, Any]:
    """Get repository status."""
    return {
        "branch": run_cmd("git branch --show-current"),
        "behind": run_cmd("git rev-list HEAD..origin/main --count"),
        "ahead": run_cmd("git rev-list origin/main..HEAD --count"),
        "status": run_cmd("git status --porcelain"),
        "last_fetch": run_cmd("git log -1 --format='%ar' FETCH_HEAD") or "Unknown",
    }


def get_file_stats() -> Dict[str, Any]:
    """Get key file modification times."""
    files_to_check = [
        "src/build_canonical.py",
        "src/write_fcpxml.py",
        "src/validate_canonical.py",
        "handoff/handoff.yml",
        "tests/test_event_id_validation.py",
    ]

    stats = {}
    for filepath in files_to_check:
        path = Path(filepath)
        if path.exists():
            mtime = path.stat().st_mtime
            stats[filepath] = datetime.fromtimestamp(mtime).strftime("%H:%M:%S")
        else:
            stats[filepath] = "Missing"

    return stats


def format_handoff_status(status: Dict[str, Any]) -> str:
    """Format handoff status for display."""
    if "error" in status:
        return f"❌ {status['error']}"

    owner = status.get("owner", "Unknown")
    state = status.get("status", "Unknown")
    action = status.get("next_action", "None specified")[:80] + "..."

    # Color coding
    color = {
        "GPT": "🤖",
        "CL": "🔵",
        "CLAUDE": "🔵",
        "GEMINI": "💎",
        "COPILOT": "🔧",
        "CO": "🔧",
    }.get(owner.upper(), "❓")

    status_color = {
        "needs_implementation": "🔨",
        "needs_review": "👀",
        "needs_action": "⚡",
        "completed": "✅",
        "blocked": "🚫",
        "in_progress": "⏳",
    }.get(state, "❓")

    return f"{color} Owner: {owner} | {status_color} Status: {state}\n   Action: {action}"


def display_dashboard():
    """Display the monitoring dashboard."""
    clear_screen()

    print("=" * 80)
    print("🤖 MULTI-AGENT SYSTEM MONITOR")
    print("=" * 80)
    print(f"⏰ Last Update: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Handoff Status
    print("📋 CURRENT HANDOFF:")
    handoff = get_handoff_status()
    print(f"   {format_handoff_status(handoff)}")
    print()

    # Repository Status
    print("📦 REPOSITORY STATUS:")
    repo = get_repo_status()
    branch_status = f"🌿 Branch: {repo['branch']}"
    if repo["behind"] != "0":
        branch_status += f" (behind by {repo['behind']})"
    if repo["ahead"] != "0":
        branch_status += f" (ahead by {repo['ahead']})"

    print(f"   {branch_status}")

    if repo["status"]:
        print(f"   📝 Uncommitted changes: {len(repo['status'].split())}")
    else:
        print("   ✨ Working tree clean")
    print()

    # Recent Commits
    print("📝 RECENT COMMITS:")
    commits = get_recent_commits()
    for commit in commits[:3]:
        print(
            f"   {commit['hash']} | {commit['author']} | {commit['time']} | {commit['message'][:50]}..."
        )
    print()

    # File Modification Times
    print("📁 KEY FILE STATUS:")
    files = get_file_stats()
    for filepath, mtime in files.items():
        status = "🟢" if mtime != "Missing" else "🔴"
        print(f"   {status} {filepath.ljust(35)} | Modified: {mtime}")
    print()

    # Instructions
    print("🔧 CONTROLS:")
    print("   Ctrl+C to exit | Updates every 10 seconds")
    print("   Run: git fetch && git pull  (to sync with remote)")
    print()

    # Action recommendations
    if repo["behind"] != "0":
        print("⚠️  RECOMMENDATION: Run 'git pull' to get latest changes")

    if handoff.get("status") == "blocked":
        print("🚨 ATTENTION: Handoff is blocked - manual intervention needed")
    elif handoff.get("owner") in ["GPT", "GEMINI"] and datetime.now().hour > 0:
        print("ℹ️  WAITING: Automated agent should be processing...")

    print("=" * 80)


def main():
    """Main monitoring loop."""
    try:
        while True:
            display_dashboard()
            time.sleep(10)  # Update every 10 seconds
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped. Your multi-agent system continues running.")
        print("💡 Check GitHub Actions: https://github.com/odgriff79/aaf2resolve-spec/actions")


if __name__ == "__main__":
    main()
