#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adk.utils.memory_store import read_entry, write_entry

try:
    from adk.utils.memory_store import list_entries  # type: ignore
except Exception:  # list not available
    list_entries = None  # type: ignore

try:
    from adk.utils.memory_store import list_entries  # type: ignore
except Exception:  # list not available
    list_entries = None  # type: ignore


def main():
    if len(sys.argv) < 2:
        print("Usage: python memory_cli.py write <key> <json_value>")
        print("       python memory_cli.py read <key>")
        print("       python memory_cli.py list")
        return 1

    command = sys.argv[1]

    if command == "write" and len(sys.argv) >= 4:
        key = sys.argv[2]
        try:
            value = json.loads(sys.argv[3])
            write_entry(key, value, author="human")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            return 1

    elif command == "list":
        if callable(list_entries):
            entries = list_entries()  # expected: iterable of dicts with at least a "key"
            # print sorted keys; if entries are dicts, pull "key"; if already strings, use directly
            keys = []
            for e in entries:
                try:
                    keys.append(e["key"])
                except Exception:
                    keys.append(str(e))
            for k in sorted(set(keys)):
                print(k)
        else:
            print("List operation not supported by memory store")
            return 1

    elif command == "list":
        if callable(list_entries):
            entries = list_entries()  # expected: iterable of dicts with at least a "key"
            # print sorted keys; if entries are dicts, pull "key"; if already strings, use directly
            keys = []
            for e in entries:
                try:
                    keys.append(e["key"])
                except Exception:
                    keys.append(str(e))
            for k in sorted(set(keys)):
                print(k)
        else:
            print("List operation not supported by memory store")
            return 1

    elif command == "read" and len(sys.argv) >= 3:
        key = sys.argv[2]
        entry = read_entry(key)
        if entry:
            print(json.dumps(entry, indent=2))
        else:
            print("Entry not found")

    else:
        print("Invalid command or arguments")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
