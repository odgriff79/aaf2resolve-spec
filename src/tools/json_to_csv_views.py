#!/usr/bin/env python3
"""
JSON to CSV Views

Legacy utility: Flattens canonical JSON (see /docs/data_model_json.md) to CSV tables
for spreadsheet viewing or old-school analysis.

Not part of the main pipeline.

"""

import argparse
import json
import csv
import sys


def events_to_csv(json_data, out_file):
    # TODO: Implement real CSV flattening.
    # For demo, just dump all event basics.
    project = json_data.get("project", {})
    for timeline in project.get("timelines", []):
        for event in timeline.get("events", []):
            row = {
                "timeline": timeline["name"],
                "event_id": event["id"],
                "type": event["type"],
                "start": event.get("start"),
                "duration": event.get("duration"),
                "track": event.get("track"),
                "source": event.get("source"),
            }
            out_file.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Flatten canonical JSON events to CSV")
    parser.add_argument("json", help="Input canonical JSON")
    parser.add_argument("-o", "--output", help="Output CSV file (default: stdout)")
    args = parser.parse_args()

    with open(args.json) as f:
        data = json.load(f)

    fieldnames = [
        "timeline",
        "event_id",
        "type",
        "start",
        "duration",
        "track",
        "source",
    ]
    if args.output:
        with open(args.output, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            events_to_csv(data, writer)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        events_to_csv(data, writer)


if __name__ == "__main__":
    main()
