#!/usr/bin/env python3
"""Import/audit NJ Transit without modifying the published schedule or metadata."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from gtfs_importer import NORMALIZED_TABLES, download_zip, import_feed, write_csv
from njt import njt_feed_config, validate_njt_result

ROOT = Path(__file__).resolve().parents[2]


def prepare(source_zip: Path | None, output: Path, today: dt.date | None = None) -> dict:
    if output.exists():
        raise FileExistsError(output)
    # A fresh workspace prevents failed imports from touching even staged prior data.
    config = njt_feed_config(today=today)
    with tempfile.TemporaryDirectory(prefix="moose_njt_") as directory:
        staging_root = Path(directory)
        source = staging_root / "supporting_files/source_gtfs/njt/rail_data.zip"
        source.parent.mkdir(parents=True)
        if source_zip is None:
            download_zip(config.url, source)
        else:
            shutil.copyfile(source_zip, source)
        result = import_feed(staging_root, config, lambda name: name, download=False)
        validate_njt_result(result, today)
        with zipfile.ZipFile(source) as archive:
            # Names only: the importer currently does not normalize fare tables.
            fare_files = sorted(name for name in archive.namelist() if Path(name).name.startswith("fare_"))
        services = collections.Counter(row["service_name"] for row in result.normalized["trips"])
        report = {
            "source_url": config.url,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "imported_at": result.metadata["imported_at"],
            "service_start": min(row["service_start_date"] for row in result.rows),
            "service_end": max(row["service_end_date"] for row in result.rows),
            "trips_by_service": dict(sorted(services.items())),
            "stop_events": len(result.rows),
            "source_stops": len(result.normalized["stops"]),
            "canonical_stations": len(result.normalized["canonical_stations"]),
            "fare_files": fare_files,
            "published": False,
            "publication_note": "Isolated source audit; the normal build imports schedules and prepares corroborated fares separately.",
            "warnings": result.warnings,
        }
        # Write only after validation; output must be a dedicated new directory.
        output.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source, output / "rail_data.zip")
        result.normalized["feeds"][0]["zip_path"] = str((output / "rail_data.zip").resolve())
        for name, columns in NORMALIZED_TABLES.items():
            write_csv(output / "normalized_gtfs" / f"{name}.csv", columns, result.normalized[name])
        with gzip.open(output / "schedule.csv.gz", "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result.rows[0]))
            writer.writeheader()
            writer.writerows(result.rows)
        (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Use a downloaded official ZIP instead of downloading it")
    parser.add_argument("--output", type=Path, default=ROOT / "supporting_files/staging/njt",
                        help="New staging directory; existing directories are never overwritten")
    args = parser.parse_args()
    report = prepare(args.zip, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
