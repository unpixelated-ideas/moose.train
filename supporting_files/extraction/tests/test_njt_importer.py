from __future__ import annotations

import datetime as dt
import gzip
import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from test_gtfs_importer import base_files, write_gtfs_zip
from gtfs_importer import default_feed_configs, import_feed, import_configured_feeds
from njt import ROUTES, njt_feed_config, validate_njt_result
from prepare_njt import prepare

TODAY = dt.date(2026, 10, 19)
ROUTE_IDS = dict(zip(("1", "2", "3", "5", "6", "7", "8", "9", "10", "11", "12", "14", "15", "16"), ROUTES))


def njt_files():
    files = base_files()
    files["routes.txt"] = [dict(route_id=key, agency_id="A1", route_short_name=code,
                                route_long_name=ROUTES[code], route_type="2") for key, code in ROUTE_IDS.items()]
    files["routes.txt"].append(dict(route_id="4", agency_id="A1", route_short_name="HBLR",
                                    route_long_name="Hudson-Bergen Light Rail", route_type="0"))
    names = {"105": "NEW YORK PENN STATION", "107": "NEWARK PENN STATION",
             "38174": "SECAUCUS LOWER LEVEL", "38187": "SECAUCUS UPPER LEVEL",
             "63": "HOBOKEN", "123": "PORT JERVIS", "142": "SPRING VALLEY"}
    files["stops.txt"] = [dict(stop_id=key, stop_name=name, stop_lat="0", stop_lon="0")
                           for key, name in names.items()]
    files["trips.txt"] = []
    files["stop_times.txt"] = []
    core_stops = {"6": ["123", "38174", "63"], "10": ["107", "38187", "105"],
                  "14": ["142", "38174", "63"]}
    for route in (*core_stops, *(key for key in ROUTE_IDS if key not in core_stops), "4"):
        stops = core_stops.get(route, ["38174", "63"])
        for direction in ("0", "1"):
            trip_id = f"internal-{route}-{direction}"
            files["trips.txt"].append(dict(route_id=route, service_id="S1", trip_id=trip_id,
                                             trip_headsign="HOBOKEN", direction_id=direction,
                                             block_id=f"{route}{direction}42"))
            for index, stop_id in enumerate(stops if direction == "0" else list(reversed(stops))):
                files["stop_times.txt"].append(dict(trip_id=trip_id, arrival_time=f"{24+index}:05:00",
                    departure_time=f"{24+index}:06:00", stop_id=stop_id, stop_sequence=str(index+1),
                    pickup_type="1" if index == 2 else "0", drop_off_type="1" if index == 0 else "0"))
    files["calendar.txt"] = []
    files["calendar_dates.txt"] = [dict(service_id="S1", date="20261019", exception_type="1"),
                                    dict(service_id="S1", date="20261020", exception_type="1")]
    return files


class NjtImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = njt_files()

    def import_fixture(self):
        write_gtfs_zip(self.root, "njt", "rail_data.zip", self.files)
        return import_feed(self.root, njt_feed_config(today=TODAY), lambda name: "UNMAPPED", download=False)

    def test_scope_train_numbers_through_trips_and_source_identity(self):
        result = self.import_fixture()
        validate_njt_result(result, TODAY)
        self.assertEqual(len(result.normalized["trips"]), 2 * len(ROUTES))
        self.assertEqual(len(result.rows), 18 + 4 * (len(ROUTES) - 3))
        self.assertEqual({r["service_name"] for r in result.rows}, set(ROUTES.values()))
        trip = [r for r in result.rows if "gtfs_trip_id=internal-6-0;" in r["raw_notes"]]
        self.assertEqual([r["station_id"] for r in trip], ["NJT_123", "SEC", "NJT_63"])
        self.assertEqual({r["train_number"] for r in trip}, {"6042"})
        self.assertEqual(trip[0]["arrival_time"], "24:05")
        self.assertIn("pickup_type=1", trip[-1]["raw_notes"])
        self.assertEqual(trip[0]["service_start_date"], "2026-10-19")
        self.assertEqual(trip[0]["service_end_date"], "2026-10-20")
        self.assertEqual(result.normalized["trips"][0]["source_trip_id"], "internal-6-0")

    def test_seasonal_route_removal_can_renumber_other_routes(self):
        meadowlands_trips = {t["trip_id"] for t in self.files["trips.txt"] if t["route_id"] == "9"}
        self.files["stop_times.txt"] = [s for s in self.files["stop_times.txt"]
                                        if s["trip_id"] not in meadowlands_trips]
        for table in ("routes.txt", "trips.txt"):
            self.files[table] = [row for row in self.files[table] if row["route_id"] != "9"]
            for row in self.files[table]:
                route_id = int(row["route_id"])
                if route_id > 9:
                    row["route_id"] = str(route_id - 1)
        result = self.import_fixture()
        validate_njt_result(result, TODAY)
        self.assertEqual({r["service_name"] for r in result.rows},
                         set(ROUTES.values()) - {"Meadowlands Rail Line"})
        northeast = next(r for r in result.normalized["routes"] if r["source_route_id"] == "9")
        self.assertEqual(northeast["service_name"], "Northeast Corridor")

    def test_secaucus_levels_share_station_without_losing_source_stops(self):
        result = self.import_fixture()
        stops = [s for s in result.normalized["stops"] if s["canonical_station_id"] == "SEC"]
        self.assertEqual({s["source_stop_id"] for s in stops}, {"38174", "38187"})
        self.assertEqual({s["canonical_station_id"] for s in result.normalized["stops"]
                          if s["source_stop_id"] in {"105", "107"}}, {"NYP", "NWK"})

    def test_staging_isolated_from_published_schedule_and_metadata(self):
        self.import_fixture()
        source = self.root / "supporting_files/source_gtfs/njt/rail_data.zip"
        output = self.root / "staging"
        report = prepare(source, output, TODAY)
        self.assertFalse(report["published"])
        self.assertEqual(report["fare_files"], [])
        self.assertEqual(report["trips_by_service"]["Port Jervis Line"], 2)
        self.assertFalse((self.root / "moose_train_schedule.csv.gz").exists())
        self.assertFalse((self.root / "supporting_files/extraction/gtfs_import_metadata.csv").exists())
        with gzip.open(output / "schedule.csv.gz", "rt") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 18 + 4 * (len(ROUTES) - 3))
        self.assertEqual(json.loads((output / "audit.json").read_text()), report)
        with self.assertRaises(FileExistsError):
            prepare(source, output, TODAY)

    def test_unmapped_stop_rejected_before_output(self):
        self.files["stops.txt"][0]["stop_id"] = "NEW_STOP"
        for stop in self.files["stop_times.txt"]:
            if stop["stop_id"] == "105":
                stop["stop_id"] = "NEW_STOP"
        self.import_fixture()
        source = self.root / "supporting_files/source_gtfs/njt/rail_data.zip"
        output = self.root / "staging"
        with self.assertRaisesRegex(ValueError, "Unmapped"):
            prepare(source, output, TODAY)
        self.assertFalse(output.exists())

    def test_missing_line_and_changed_route_rejected(self):
        self.files["trips.txt"] = [t for t in self.files["trips.txt"] if t["route_id"] != "14"]
        with self.assertRaisesRegex(ValueError, "missing or expired service: Pascack Valley"):
            validate_njt_result(self.import_fixture(), TODAY)
        self.files = njt_files()
        self.files["routes.txt"][0]["route_long_name"] = "Changed line"
        with self.assertRaisesRegex(ValueError, "changed"):
            validate_njt_result(self.import_fixture(), TODAY)

    def test_expired_or_one_direction_service_rejected(self):
        with self.assertRaisesRegex(ValueError, "expired"):
            validate_njt_result(self.import_fixture(), dt.date(2026, 11, 1))
        self.files["trips.txt"] = [t for t in self.files["trips.txt"] if t["direction_id"] == "0"]
        with self.assertRaisesRegex(ValueError, "both directions"):
            validate_njt_result(self.import_fixture(), TODAY)

    def test_missing_train_number_rejected(self):
        self.files["trips.txt"][0]["block_id"] = ""
        with self.assertRaisesRegex(ValueError, "train number"):
            validate_njt_result(self.import_fixture(), TODAY)

    def test_replacement_bus_is_not_imported_as_a_through_train(self):
        for route_id, marker in (("6", "PJBUS"), ("8", "GBUS710")):
            source_id = f"internal-{route_id}-0"
            bus_id = f"bus-{route_id}"
            source = next(trip for trip in self.files["trips.txt"] if trip["trip_id"] == source_id)
            self.files["trips.txt"].append(dict(source, trip_id=bus_id, block_id=marker))
            self.files["stop_times.txt"].extend([
                dict(stop, trip_id=bus_id) for stop in list(self.files["stop_times.txt"])
                if stop["trip_id"] == source_id
            ])
        result = self.import_fixture()
        validate_njt_result(result, TODAY)
        self.assertEqual(len(result.normalized["trips"]), 2 * len(ROUTES))
        self.assertFalse(any("PJBUS" in row["train_number"] for row in result.rows))
        self.assertTrue(any("Excluded 1 trips" in warning and "PJBUS" in warning for warning in result.warnings))
        self.assertTrue(any("Excluded 1 trips" in warning and "GBUS" in warning for warning in result.warnings))

    def test_unknown_bus_marker_requires_review(self):
        self.files["trips.txt"][0]["block_id"] = "OTHER_BUS"
        with self.assertRaisesRegex(ValueError, "replacement bus"):
            validate_njt_result(self.import_fixture(), TODAY)

    def test_reused_source_stop_id_cannot_silently_become_penn_station(self):
        self.files["stops.txt"][0]["stop_name"] = "DIFFERENT STATION"
        with self.assertRaisesRegex(ValueError, "source stop name changed"):
            validate_njt_result(self.import_fixture(), TODAY)

    def test_operator_in_default_public_refresh(self):
        self.assertIn("njt", {config.feed_id for config in default_feed_configs() if config.enabled})

    def test_failed_source_validation_preserves_previous_normalized_feed(self):
        self.import_fixture()
        config = njt_feed_config(today=TODAY)
        import_configured_feeds(self.root, lambda name: "UNMAPPED", download=False, configs=[config])
        target = self.root / "supporting_files/extraction/normalized_gtfs/njt/trips.csv"
        original = target.read_bytes()
        extracted = self.root / "supporting_files/source_gtfs/njt/feed/trips.txt"
        previous_extracted = extracted.read_bytes()
        self.files["trips.txt"][0]["block_id"] = "UNREVIEWED_BUS"
        write_gtfs_zip(self.root, "njt", "rail_data.zip", self.files)
        rows, metadata, results = import_configured_feeds(
            self.root, lambda name: "UNMAPPED", download=False, configs=[config])
        self.assertEqual(rows, [])
        self.assertEqual(metadata[0]["success"], "false")
        self.assertTrue(results[0].errors)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(extracted.read_bytes(), previous_extracted)


if __name__ == "__main__":
    unittest.main()
