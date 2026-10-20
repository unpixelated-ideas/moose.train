import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("package_site", ROOT / "supporting_files/scripts/package_site.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScheduleStorageTests(unittest.TestCase):
    def test_package_restores_plain_csv_and_keeps_compressed_source_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "supporting_files/assets").mkdir(parents=True)
            exports = root / "supporting_files/extraction/source_csvs"
            exports.mkdir(parents=True)
            data = b"station_id,station_name\r\nPOU,Poughkeepsie\r\n"
            (root / "moose_train_schedule.csv.gz").write_bytes(gzip.compress(data, mtime=0))
            (exports / "mnr_gtfs_test.csv.gz").write_bytes(gzip.compress(data, mtime=0))
            staging = root / "supporting_files/staging/njt"
            staging.mkdir(parents=True)
            (staging / "unreleased.csv").write_text("Unverified NJ Transit data")
            with patch.object(MODULE, "ROOT", root):
                MODULE.main()
            self.assertEqual((root / "_site/moose_train_schedule.csv").read_bytes(), data)
            self.assertEqual(gzip.decompress((root / "_site/supporting_files/extraction/source_csvs/mnr_gtfs_test.csv.gz").read_bytes()), data)
            self.assertFalse((root / "_site/moose_train_schedule.csv.gz").exists())
            self.assertFalse((root / "_site/supporting_files/staging").exists())

    def test_extractor_gzip_is_lossless_and_deterministic(self):
        from extract_timetables import write_csv
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.csv.gz"
            write_csv(path, ["station_id", "station_name"], [dict(station_id="POU", station_name="Poughkeepsie")])
            first = path.read_bytes()
            write_csv(path, ["station_id", "station_name"], [dict(station_id="POU", station_name="Poughkeepsie")])
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(gzip.decompress(first), b"station_id,station_name\r\nPOU,Poughkeepsie\r\n")
