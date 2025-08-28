# AAF to Resolve FCPXML Converter

This project provides a robust, JSON-first pipeline to convert Avid AAF sequences into FCPXML 1.13 files for import into DaVinci Resolve, without relying on the proprietary Resolve API. The process consists of:

1. Parsing AAF files into a canonical, well-documented JSON schema.
2. Loading JSON into a normalized SQLite database (for analysis or migration).
3. Exporting FCPXML 1.13, suitable for import into DaVinci Resolve, from the canonical JSON format.

**Key Features:**
- Canonical, annotated JSON schema for interchange.
- Full SQLite relational schema for validation and transformation.
- FCPXML output adheres to key Resolve requirements (frame duration, timecode, asset mapping, etc.).
- No proprietary or closed-source dependencies (uses [pyaaf2](https://github.com/markreidvfx/pyaaf2)).

**Directory Structure:**
- `/docs`: Data model, database schema, FCPXML rules/specs.
- `/src`: CLI tools for AAF parsing, FCPXML writing, DB loading, and optional CSV extraction.
- `/tests`: Holds sample AAFs and expected outputs for validation.

See `/docs/project_brief.md` for the full design brief.

## Design docs

- [Canonical JSON Data Model](docs/data_model_json.md)
- [FCPXML 1.13 Rules](docs/fcpxml_rules.md)
- [SQLite Schema](docs/db_schema.sql)
- **In-Memory Canonical Pipeline** → [`docs/in_memory_pipeline.md`](docs/in_memory_pipeline.md)
- **Inspector Rule Pack (Traversal, UMID, Effects)** → [`docs/inspector_rule_pack.md`](docs/inspector_rule_pack.md)
- **Backlog / Task Board** → [`docs/backlog.md`](docs/backlog.md)
