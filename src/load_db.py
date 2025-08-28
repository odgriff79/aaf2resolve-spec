#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
load_db.py — SPEC-FIRST SCAFFOLD (no implementation yet)

Purpose:
  Load canonical JSON into an **optional SQLite database** for validation,
  analytics, and queries. The DB is never required for writers; it exists
  only as a helper tool for analysis.

Authoritative specs:
  - docs/db_schema.sql                  (defines the normalized relational model)
  - docs/data_model_json.md             (canonical JSON contract; must be the source)
  - docs/project_brief.md               (design goals and context)

Key principles:
  • DB is optional: Writers and downstream tools must consume canonical JSON,
    not the database.
  • Lossless import: All fields from canonical JSON must be represented.
  • Fidelity: No rewriting of paths, values, or identifiers when inserting.
  • Traceability: Every row in the DB must link back to its canonical event id.
"""

from __future__ import annotations
from typing import Dict, Any
import argparse
import json
import sqlite3
import sys


# --------------------------- Public API ---------------------------

def load_canonical_into_db(canon: Dict[str, Any], db_path: str) -> None:
    """
    Load canonical JSON into a SQLite database at `db_path`.

    Input contract:
      - canon MUST match docs/data_model_json.md exactly.
      - Required keys always present; unknowns as null.

    DB contract (docs/db_schema.sql):
      - Tables:
          * project
          * timeline
          * events
          * sources
          * effects
          * keyframes
          * external_refs
      - Each row corresponds 1:1 with canonical JSON objects/fields.
      - event_id stable across all tables (foreign key).

    MUSTS:
      - Preserve path strings and UMID chain exactly.
      - Insert null where canonical JSON has null (don’t omit).
      - Use transactions for atomic insert.

    TODO(impl):
      - Create schema from docs/db_schema.sql if not present.
      - Insert project row.
      - Insert timeline row.
      - Insert events; link sources/effects/keyframes/external_refs via event_id.
    """
    raise NotImplementedError("Spec scaffold: implement per docs/db_schema.sql")


# --------------------------- CLI (spec harness) ---------------------------

def main(argv: list[str] | None = None) -> int:
    """
    CLI:
      python -m src.load_db canonical.json -o db.sqlite

    Behavior:
      - Loads canonical JSON from file.
      - Writes/overwrites SQLite DB at db.sqlite per docs/db_schema.sql.

    NOTE:
      - This CLI must not alter canonical values.
      - DB is optional — use only when analysis/queries needed.
    """
    ap = argparse.ArgumentParser(description="Load canonical JSON into SQLite (spec-first scaffold).")
    ap.add_argument("canon_json", help="Path to canonical JSON file")
    ap.add_argument("-o", "--out", required=True, help="Output SQLite DB path")
    args = ap.parse_args(argv)

    with open(args.canon_json, "r", encoding="utf-8") as f:
        canon: Dict[str, Any] = json.load(f)

    load_canonical_into_db(canon, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
