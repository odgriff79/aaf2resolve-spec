#!/usr/bin/env python3
"""
Load Canonical JSON into SQLite DB

Loads canonical JSON (see /docs/data_model_json.md) into a normalized SQLite
database as defined in /docs/db_schema.sql.

Can initialize, reset, or append to the DB.

"""

import argparse
import json
import sqlite3
import os

def load_schema(conn, schema_path):
    with open(schema_path) as f:
        conn.executescript(f.read())

def json_to_db(json_data, conn):
    # TODO: Implement real DB population logic.
    # See docs/db_schema.sql for schema.
    pass

def main():
    parser = argparse.ArgumentParser(description="Load canonical JSON into SQLite DB")
    parser.add_argument("json", help="Input canonical JSON")
    parser.add_argument("db", help="SQLite DB file")
    parser.add_argument("--init", action="store_true", help="(Re)initialize DB schema")
    parser.add_argument("--schema", default=os.path.join(os.path.dirname(__file__), "..", "docs", "db_schema.sql"),
                        help="Path to schema SQL (default: docs/db_schema.sql)")
    args = parser.parse_args()

    with open(args.json) as f:
        data = json.load(f)

    conn = sqlite3.connect(args.db)

    if args.init:
        load_schema(conn, args.schema)

    json_to_db(data, conn)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()