"""Reject failed, empty, or expired products before uploading a Pages artifact."""
import csv
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {"mnr", "hartford", "sle", "amtrak"}


def validate(root=ROOT, today=None):
    today = today or dt.datetime.now(ZoneInfo("America/New_York")).date()
    with (root / "supporting_files/extraction/gtfs_import_metadata.csv").open() as handle:
        metadata = list(csv.DictReader(handle))
    if {row["feed_id"] for row in metadata} != EXPECTED or len(metadata) != len(EXPECTED):
        raise ValueError("Expected exactly four GTFS products")
    for row in metadata:
        if row["success"] != "true" or json.loads(row["errors"]):
            raise ValueError(f"Failed import: {row['feed_id']}")
        if not json.loads(row["record_counts"]).get("stop_times", 0):
            raise ValueError(f"Empty import: {row['feed_id']}")
    coverage = {feed: False for feed in EXPECTED}
    with (root / "moose_train_schedule.csv").open() as handle:
        for row in csv.DictReader(handle):
            feed = next((feed for feed in EXPECTED if row["source_pdf"].startswith(feed + "_gtfs_")), None)
            if feed is None:
                continue
            if row["service_dates"]:
                active = any(dt.date.fromisoformat(day) >= today for day in row["service_dates"].split(","))
            else:
                active = dt.date.fromisoformat(row["service_end_date"]) >= today
            coverage[feed] |= active
    missing = [feed for feed, active in coverage.items() if not active]
    if missing:
        raise ValueError(f"No current or future service for: {', '.join(missing)}")
    print("All four products imported successfully with current or future service.")


if __name__ == "__main__":
    validate()
