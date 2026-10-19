import csv
import gzip
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "validate_refresh", Path(__file__).resolve().parents[2] / "scripts/validate_refresh.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RefreshValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "supporting_files/extraction").mkdir(parents=True)
        self.metadata = [dict(feed_id=feed, success="true", errors="[]",
                              record_counts=json.dumps({"stop_times": 10}))
                         for feed in sorted(MODULE.EXPECTED)]
        self.rows = [dict(source_pdf=feed + "_gtfs_example.zip", service_dates="",
                          service_end_date="2026-11-01", service_name="") for feed in sorted(MODULE.EXPECTED)]

        for name in ["Hudson Line", "Harlem Line", "New Haven Line", "New Canaan Branch", "Danbury Branch", "Waterbury Branch"]:
            self.rows.append(dict(source_pdf="mnr_gtfs_example.zip", service_dates="",
                                  service_end_date="2026-11-01", service_name=name))

    def test_missing_hudson_line_rejected(self):
        self.rows = [row for row in self.rows if row["service_name"] != "Hudson Line"]
        with self.assertRaisesRegex(ValueError, "Metro-North service for: Hudson Line"):
            self.check()

    def test_expired_harlem_line_rejected(self):
        next(row for row in self.rows if row["service_name"] == "Harlem Line")["service_end_date"] = "2026-10-01"
        with self.assertRaisesRegex(ValueError, "Metro-North service for: Harlem Line"):
            self.check()

    def test_compressed_snapshot_without_plaintext_csv(self):
        self.compressed = True
        self.check()
        self.assertFalse((self.root / "moose_train_schedule.csv").exists())

    def check(self):
        for relative, rows in [("supporting_files/extraction/gtfs_import_metadata.csv", self.metadata),
                               ("moose_train_schedule.csv", self.rows)]:
            path = self.root / relative
            if getattr(self, "compressed", False) and relative == "moose_train_schedule.csv":
                handle = gzip.open(str(path) + ".gz", "wt", newline="")
            else:
                handle = path.open("w", newline="")
            with handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        MODULE.validate(self.root, dt.date(2026, 10, 17))

    def test_complete_refresh_and_comma_separated_dates(self):
        self.rows[0]["service_dates"] = "2026-10-01,2026-11-01"
        self.check()

    def test_failed_feed_rejected(self):
        self.metadata[0]["success"] = "false"
        with self.assertRaisesRegex(ValueError, "Failed import"):
            self.check()

    def test_missing_product_rejected(self):
        self.metadata.pop()
        with self.assertRaisesRegex(ValueError, "exactly five"):
            self.check()

    def test_empty_feed_rejected(self):
        self.metadata[0]["record_counts"] = '{"stop_times": 0}'
        with self.assertRaisesRegex(ValueError, "Empty import"):
            self.check()

    def test_expired_explicit_dates_rejected(self):
        self.rows[0]["service_dates"] = "2026-10-01,2026-10-02"
        with self.assertRaisesRegex(ValueError, "No current or future"):
            self.check()

    def test_expired_regular_service_rejected(self):
        self.rows[0]["service_end_date"] = "2026-10-01"
        with self.assertRaisesRegex(ValueError, "No current or future"):
            self.check()
