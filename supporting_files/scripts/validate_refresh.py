"""Reject failed, empty, or expired products before uploading a Pages artifact."""
import csv
import gzip
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {"mnr", "hartford", "sle", "amtrak", "lirr", "njt"}


def validate(root=ROOT, today=None):
    today = today or dt.datetime.now(ZoneInfo("America/New_York")).date()
    with (root / "supporting_files/extraction/gtfs_import_metadata.csv").open() as handle:
        metadata = list(csv.DictReader(handle))
    if {row["feed_id"] for row in metadata} != EXPECTED or len(metadata) != len(EXPECTED):
        raise ValueError("Expected exactly six GTFS products")
    for row in metadata:
        if row["success"] != "true" or json.loads(row["errors"]):
            raise ValueError(f"Failed import: {row['feed_id']}")
        if not json.loads(row["record_counts"]).get("stop_times", 0):
            raise ValueError(f"Empty import: {row['feed_id']}")
    coverage = {feed: False for feed in EXPECTED}
    mnr_services = {name: False for name in ["Hudson Line", "Harlem Line", "New Haven Line", "New Canaan Branch", "Danbury Branch", "Waterbury Branch"]}
    njt_services = {name: False for name in ["Northeast Corridor", "Port Jervis Line", "Pascack Valley Line"]}
    compressed = root / "moose_train_schedule.csv.gz"
    schedule = gzip.open(compressed, "rt", encoding="utf-8") if compressed.exists() else (root / "moose_train_schedule.csv").open()
    with schedule as handle:
        for row in csv.DictReader(handle):
            feed = next((feed for feed in EXPECTED if row["source_pdf"].startswith(feed + "_gtfs_")), None)
            if feed is None:
                continue
            if row["service_dates"]:
                active = any(dt.date.fromisoformat(day) >= today for day in row["service_dates"].split(","))
            else:
                active = dt.date.fromisoformat(row["service_end_date"]) >= today
            coverage[feed] |= active
            if feed == "mnr" and row.get("service_name") in mnr_services:
                mnr_services[row["service_name"]] |= active
            if feed == "njt" and row.get("service_name") in njt_services:
                njt_services[row["service_name"]] |= active
            if feed == "njt" and not row["train_number"].isdigit():
                raise ValueError("Unreviewed NJ Transit train or replacement bus")
    missing = [feed for feed, active in coverage.items() if not active]
    if missing:
        raise ValueError(f"No current or future service for: {', '.join(missing)}")
    missing_lines = [name for name, active in mnr_services.items() if not active]
    if missing_lines:
        raise ValueError(f"No current or future Metro-North service for: {', '.join(missing_lines)}")
    missing_njt = [name for name, active in njt_services.items() if not active]
    if missing_njt:
        raise ValueError(f"No current or future NJ Transit service for: {', '.join(missing_njt)}")
    print("All six products imported successfully with current or future service.")


if __name__ == "__main__":
    validate()
