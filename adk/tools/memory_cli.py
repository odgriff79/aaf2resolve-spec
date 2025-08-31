#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adk.utils.memory_store import write_entry, read_entry

def main():
    if len(sys.argv) < 2:
        print("Usage: python memory_cli.py write <key> <json_value>")
        print("       python memory_cli.py read <key>")
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
