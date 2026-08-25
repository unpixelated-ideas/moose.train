from __future__ import annotations

import csv
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gtfs_importer import GtfsFeedConfig, RouteFilter, import_configured_feeds, import_feed


def station_id_for(name: str) -> str:
    return {
        "Grand Central": "GCT",
        "New Haven": "NHV",
        "New Haven Union": "NHV",
        "New Haven State Street": "STS",
        "New York Penn": "NYP",
        "Stamford": "STM",
        "New Haven Union Station": "NHV",
        "Hartford": "HFD",
        "Old Saybrook": "OSB",
        "Springfield": "SPG",
        "Westerly": "WLY",
        "New London": "NLC",
    }.get(name, name.upper().replace(" ", "_")[:12])


def write_gtfs_zip(root: Path, feed_id: str, zip_name: str, files: dict[str, list[dict[str, str]]]) -> None:
    target = root / "supporting_files" / "source_gtfs" / feed_id / zip_name
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w") as archive:
        for filename, rows in files.items():
            if rows:
                headers = list(rows[0])
            else:
                headers = default_headers(filename)
            lines = [",".join(headers)]
            for row in rows:
                lines.append(",".join(str(row.get(header, "")) for header in headers))
            archive.writestr(filename, "\n".join(lines) + "\n")


def default_headers(filename: str) -> list[str]:
    return {
        "agency.txt": ["agency_id", "agency_name", "agency_url", "agency_timezone"],
        "routes.txt": ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
        "trips.txt": ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id"],
        "stop_times.txt": ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "pickup_type", "drop_off_type"],
        "stops.txt": ["stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"],
        "calendar.txt": ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
        "calendar_dates.txt": ["service_id", "date", "exception_type"],
    }[filename]


def base_files(route_id: str = "R1", agency_id: str = "A1", service_id: str = "S1") -> dict[str, list[dict[str, str]]]:
    return {
        "agency.txt": [{"agency_id": agency_id, "agency_name": "Test Agency", "agency_url": "https://example.com", "agency_timezone": "America/New_York"}],
        "routes.txt": [{"route_id": route_id, "agency_id": agency_id, "route_short_name": "", "route_long_name": "Test Rail", "route_type": "2"}],
        "trips.txt": [{"route_id": route_id, "service_id": service_id, "trip_id": "T1", "trip_headsign": "New Haven", "trip_short_name": "100", "direction_id": "0"}],
        "stop_times.txt": [
            {"trip_id": "T1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "S_A", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "T1", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "S_B", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
        ],
        "stops.txt": [
            {"stop_id": "S_A", "stop_code": "", "stop_name": "Grand Central", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "S_B", "stop_code": "", "stop_name": "New Haven", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
        ],
        "calendar.txt": [{"service_id": service_id, "monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0", "start_date": "20260720", "end_date": "20260731"}],
        "calendar_dates.txt": [],
    }


AMTRAK_SCOPE_STOP_IDS = {"NYP", "STM", "NHV", "NLC", "HFD", "SPG", "WLY", "OSB"}


def amtrak_config() -> GtfsFeedConfig:
    return GtfsFeedConfig(
        "amtrak",
        "Amtrak",
        "https://content.amtrak.com/content/gtfs/GTFS.zip",
        source_id="amtrak_official",
        zip_filename="GTFS.zip",
        route_filter=RouteFilter(include_agency_ids={"51"}, include_route_types={"2"}),
        in_scope_stop_ids=AMTRAK_SCOPE_STOP_IDS,
        min_in_scope_stops=2,
        emit_only_in_scope_stops=True,
        stop_name_aliases={
            "Ny Moynihan Train Hall At Penn": "New York Penn",
            "Stamford Amtrak": "Stamford",
            "New Haven": "New Haven Union",
            "New London": "New London",
            "Hartford Amtrak": "Hartford",
            "Springfield": "Springfield",
            "Westerly Amtrak": "Westerly",
            "Old Saybrook Amtrak": "Old Saybrook",
        },
        stop_id_station_names={"NYP": "New York Penn", "NHV": "New Haven Union"},
    )


def amtrak_files() -> dict[str, list[dict[str, str]]]:
    return {
        "agency.txt": [
            {"agency_id": "51", "agency_name": "Amtrak", "agency_url": "https://www.amtrak.com", "agency_timezone": "America/New_York"},
            {"agency_id": "1230", "agency_name": "Shore Line East", "agency_url": "https://shorelineeast.com", "agency_timezone": "America/New_York"},
        ],
        "routes.txt": [
            {"route_id": "88", "agency_id": "51", "route_short_name": "", "route_long_name": "Northeast Regional", "route_type": "2"},
            {"route_id": "94", "agency_id": "51", "route_short_name": "", "route_long_name": "Acela", "route_type": "2"},
            {"route_id": "85", "agency_id": "51", "route_short_name": "", "route_long_name": "Vermonter", "route_type": "2"},
            {"route_id": "VF", "agency_id": "51", "route_short_name": "", "route_long_name": "Valley Flyer", "route_type": "2"},
            {"route_id": "BUS", "agency_id": "51", "route_short_name": "", "route_long_name": "Amtrak Thruway Connecting Service", "route_type": "3"},
            {"route_id": "SLE", "agency_id": "1230", "route_short_name": "", "route_long_name": "Commuter Rail", "route_type": "2"},
        ],
        "trips.txt": [
            {"route_id": "88", "service_id": "S1", "trip_id": "NER1", "trip_headsign": "Washington", "trip_short_name": "95", "direction_id": "0"},
            {"route_id": "88", "service_id": "S1", "trip_id": "NYPONLY", "trip_headsign": "Chicago", "trip_short_name": "49", "direction_id": "0"},
            {"route_id": "88", "service_id": "S1", "trip_id": "OUTSIDE", "trip_headsign": "Seattle", "trip_short_name": "7", "direction_id": "0"},
            {"route_id": "BUS", "service_id": "S1", "trip_id": "BUS1", "trip_headsign": "Hartford", "trip_short_name": "6095", "direction_id": "0"},
            {"route_id": "94", "service_id": "S1", "trip_id": "ACELA1", "trip_headsign": "Boston", "trip_short_name": "2150", "direction_id": "0"},
            {"route_id": "85", "service_id": "S1", "trip_id": "VERMONTER1", "trip_headsign": "St Albans", "trip_short_name": "54", "direction_id": "0"},
            {"route_id": "VF", "service_id": "S2", "trip_id": "VALLEY1", "trip_headsign": "Springfield", "trip_short_name": "475", "direction_id": "0"},
            {"route_id": "SLE", "service_id": "S1", "trip_id": "SLE1", "trip_headsign": "New Haven", "trip_short_name": "1633", "direction_id": "0"},
        ],
        "stop_times.txt": [
            {"trip_id": "NER1", "arrival_time": "06:00:00", "departure_time": "06:00:00", "stop_id": "BOS", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "NER1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "NYP", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "NER1", "arrival_time": "08:50:00", "departure_time": "08:52:00", "stop_id": "STM", "stop_sequence": "3", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "NER1", "arrival_time": "10:00:00", "departure_time": "10:02:00", "stop_id": "NHV", "stop_sequence": "4", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "NER1", "arrival_time": "13:00:00", "departure_time": "13:00:00", "stop_id": "WAS", "stop_sequence": "5", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "NYPONLY", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "NYP", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "NYPONLY", "arrival_time": "11:00:00", "departure_time": "11:00:00", "stop_id": "PHL", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "OUTSIDE", "arrival_time": "10:00:00", "departure_time": "10:00:00", "stop_id": "CHI", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "OUTSIDE", "arrival_time": "12:00:00", "departure_time": "12:00:00", "stop_id": "MSP", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "BUS1", "arrival_time": "07:00:00", "departure_time": "07:00:00", "stop_id": "NYP", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "BUS1", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "NHV", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "ACELA1", "arrival_time": "07:00:00", "departure_time": "07:00:00", "stop_id": "NYP", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "ACELA1", "arrival_time": "08:30:00", "departure_time": "08:30:00", "stop_id": "NHV", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "VERMONTER1", "arrival_time": "11:00:00", "departure_time": "11:00:00", "stop_id": "NYP", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "VERMONTER1", "arrival_time": "13:00:00", "departure_time": "13:00:00", "stop_id": "HFD", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "VERMONTER1", "arrival_time": "14:00:00", "departure_time": "14:00:00", "stop_id": "SPG", "stop_sequence": "3", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "VALLEY1", "arrival_time": "23:50:00", "departure_time": "23:50:00", "stop_id": "NHV", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "VALLEY1", "arrival_time": "24:30:00", "departure_time": "24:30:00", "stop_id": "HFD", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "VALLEY1", "arrival_time": "25:00:00", "departure_time": "25:00:00", "stop_id": "SPG", "stop_sequence": "3", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "SLE1", "arrival_time": "06:00:00", "departure_time": "06:00:00", "stop_id": "NLC", "stop_sequence": "1", "pickup_type": "0", "drop_off_type": "0"},
            {"trip_id": "SLE1", "arrival_time": "07:00:00", "departure_time": "07:00:00", "stop_id": "NHV", "stop_sequence": "2", "pickup_type": "0", "drop_off_type": "0"},
        ],
        "stops.txt": [
            {"stop_id": "BOS", "stop_code": "", "stop_name": "Boston", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "NYP", "stop_code": "", "stop_name": "Ny Moynihan Train Hall At Penn", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "STM", "stop_code": "", "stop_name": "Stamford Amtrak", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "NHV", "stop_code": "", "stop_name": "New Haven", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "WAS", "stop_code": "", "stop_name": "Washington", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "PHL", "stop_code": "", "stop_name": "Philadelphia", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "CHI", "stop_code": "", "stop_name": "Chicago", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "MSP", "stop_code": "", "stop_name": "St Paul", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "HFD", "stop_code": "", "stop_name": "Hartford Amtrak", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "SPG", "stop_code": "", "stop_name": "Springfield", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "WLY", "stop_code": "", "stop_name": "Westerly Amtrak", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "OSB", "stop_code": "", "stop_name": "Old Saybrook Amtrak", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
            {"stop_id": "NLC", "stop_code": "", "stop_name": "New London", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""},
        ],
        "calendar.txt": [{"service_id": "S1", "monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0", "start_date": "20260720", "end_date": "20260731"}],
        "calendar_dates.txt": [{"service_id": "S2", "date": "20260721", "exception_type": "1"}],
    }


class GtfsImporterTests(unittest.TestCase):
    def test_single_feed_import(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "one", "one.zip", base_files())
            config = GtfsFeedConfig("one", "One Rail", "https://example.com/one.zip", zip_filename="one.zip")
            result = import_feed(root, config, station_id_for, download=False)
            self.assertFalse(result.errors)
            self.assertEqual(len(result.rows), 2)
            self.assertEqual(result.rows[0]["agency"], "One Rail")
            self.assertEqual(result.normalized["routes"][0]["route_uid"], "one:R1")

    def test_multi_feed_import_and_overlapping_identifiers(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "a", "a.zip", base_files())
            write_gtfs_zip(root, "b", "b.zip", base_files())
            configs = [
                GtfsFeedConfig("a", "A Rail", "https://example.com/a.zip", zip_filename="a.zip"),
                GtfsFeedConfig("b", "B Rail", "https://example.com/b.zip", zip_filename="b.zip"),
            ]
            rows, _metadata, results = import_configured_feeds(root, station_id_for, download=False, configs=configs)
            self.assertEqual(len(rows), 4)
            route_uids = {route["route_uid"] for result in results for route in result.normalized["routes"]}
            self.assertEqual(route_uids, {"a:R1", "b:R1"})

    def test_metro_north_route_filter(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files(route_id="3")
            files["routes.txt"].append({"route_id": "1", "agency_id": "A1", "route_short_name": "", "route_long_name": "Hudson", "route_type": "2"})
            files["trips.txt"].append({"route_id": "1", "service_id": "S1", "trip_id": "HUD", "trip_headsign": "Grand Central", "trip_short_name": "900", "direction_id": "1"})
            write_gtfs_zip(root, "mnr", "mnr.zip", files)
            config = GtfsFeedConfig("mnr", "Metro-North", "https://example.com/mnr.zip", zip_filename="mnr.zip", route_filter=RouteFilter(include_route_ids={"3"}))
            result = import_feed(root, config, station_id_for, download=False)
            self.assertFalse(result.errors)
            self.assertEqual({row["source_route_id"] for row in result.normalized["routes"]}, {"3"})
            self.assertEqual({row["train_number"] for row in result.rows}, {"100"})

    def test_configured_stop_exclusion(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files()
            files["stop_times.txt"].append({"trip_id": "T1", "arrival_time": "09:30:00", "departure_time": "09:30:00", "stop_id": "YARD", "stop_sequence": "3", "pickup_type": "1", "drop_off_type": "1"})
            files["stops.txt"].append({"stop_id": "YARD", "stop_code": "", "stop_name": "Springdale MW Facility", "stop_lat": "0", "stop_lon": "0", "location_type": "0", "parent_station": ""})
            write_gtfs_zip(root, "exclude", "exclude.zip", files)
            config = GtfsFeedConfig("exclude", "Exclude Rail", "https://example.com/exclude.zip", zip_filename="exclude.zip", exclude_stop_ids={"YARD"})
            result = import_feed(root, config, station_id_for, download=False)
            self.assertFalse(result.errors)
            self.assertEqual(len(result.rows), 2)
            self.assertNotIn("YARD", {row["source_stop_id"] for row in result.normalized["stops"]})
            self.assertTrue(any("Excluded 1 stop_times" in warning for warning in result.warnings))

    def test_hartford_line_import_config(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files(route_id="HART")
            files["routes.txt"][0]["route_long_name"] = "Hartford Line"
            files["stops.txt"][1]["stop_name"] = "Hartford"
            write_gtfs_zip(root, "hartford", "hlgtfs.zip", files)
            config = GtfsFeedConfig("hartford", "CTrail", "https://ctrides.com/hlgtfs.zip", zip_filename="hlgtfs.zip", default_service_name="Hartford Line", default_route_name="Hartford Line")
            result = import_feed(root, config, station_id_for, download=False)
            self.assertFalse(result.errors)
            self.assertEqual(result.rows[0]["service_name"], "Hartford Line")

    def test_shore_line_east_filter_from_amtrak_hosted_feed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files(route_id="42948", agency_id="1230")
            files["routes.txt"].append({"route_id": "88", "agency_id": "51", "route_short_name": "", "route_long_name": "Northeast Regional", "route_type": "2"})
            files["trips.txt"].append({"route_id": "88", "service_id": "S1", "trip_id": "AMTK", "trip_headsign": "Boston", "trip_short_name": "95", "direction_id": "0"})
            write_gtfs_zip(root, "sle", "GTFS.zip", files)
            config = GtfsFeedConfig("sle", "CTrail", "https://content.amtrak.com/content/gtfs/GTFS.zip", zip_filename="GTFS.zip", route_filter=RouteFilter(include_agency_ids={"1230"}), default_service_name="Shore Line East", default_route_name="Shore Line East")
            result = import_feed(root, config, station_id_for, download=False)
            self.assertFalse(result.errors)
            self.assertEqual({row["service_name"] for row in result.rows}, {"Shore Line East"})
            self.assertEqual({row["train_number"] for row in result.rows}, {"100"})

    def test_amtrak_trip_with_two_in_scope_stations_is_included_and_clipped_for_search(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            result = import_feed(root, amtrak_config(), station_id_for, download=False)
            train_95 = [row for row in result.rows if row["train_number"] == "95"]
            self.assertEqual([row["station_id"] for row in train_95], ["NYP", "STM", "NHV"])
            self.assertTrue(all(row["agency"] == "Amtrak" for row in train_95))
            self.assertTrue(all(row["service_name"] == "Northeast Regional" for row in train_95))
            self.assertIn("source_origin=Boston", train_95[0]["raw_notes"])
            self.assertIn("source_destination=Washington", train_95[0]["raw_notes"])
            normalized_stop_names = {row["stop_name"] for row in result.normalized["stops"]}
            self.assertIn("Boston", normalized_stop_names)
            self.assertIn("Washington", normalized_stop_names)

    def test_amtrak_trip_with_only_new_york_penn_in_scope_is_excluded(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            result = import_feed(root, amtrak_config(), station_id_for, download=False)
            self.assertNotIn("49", {row["train_number"] for row in result.rows})
            self.assertTrue(any("fewer than 2 in-scope stops" in warning for warning in result.warnings))

    def test_amtrak_trip_entirely_outside_region_is_excluded(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            result = import_feed(root, amtrak_config(), station_id_for, download=False)
            self.assertNotIn("7", {row["train_number"] for row in result.rows})

    def test_amtrak_bus_trips_are_excluded_by_route_type(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            result = import_feed(root, amtrak_config(), station_id_for, download=False)
            self.assertNotIn("6095", {row["train_number"] for row in result.rows})
            self.assertTrue(any("route_type outside configured scope" in warning for warning in result.warnings))

    def test_amtrak_service_products_and_after_midnight_times_are_preserved(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            result = import_feed(root, amtrak_config(), station_id_for, download=False)
            services_by_train = {row["train_number"]: row["service_name"] for row in result.rows}
            self.assertEqual(services_by_train["2150"], "Acela")
            self.assertEqual(services_by_train["54"], "Vermonter")
            self.assertEqual(services_by_train["475"], "Valley Flyer")
            self.assertIn("24:30", {row["arrival_time"] for row in result.rows if row["train_number"] == "475"})
            self.assertEqual({row["service_dates"] for row in result.rows if row["train_number"] == "475"}, {"2026-07-21"})

    def test_amtrak_scope_stations_are_selectable_but_out_of_scope_stations_are_not_in_rows(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            result = import_feed(root, amtrak_config(), station_id_for, download=False)
            row_station_ids = {row["station_id"] for row in result.rows}
            self.assertTrue({"NYP", "STM", "NHV", "HFD", "SPG"}.issubset(row_station_ids))
            self.assertFalse({"BOS", "WAS", "PHL", "CHI"}.intersection(row_station_ids))
            scope_by_stop_id = {row["source_stop_id"]: row["in_search_scope"] for row in result.normalized["stops"]}
            self.assertEqual(scope_by_stop_id["NYP"], "true")
            self.assertEqual(scope_by_stop_id["BOS"], "false")

    def test_amtrak_source_identifiers_do_not_collide_with_other_feeds(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            write_gtfs_zip(root, "other", "other.zip", base_files(route_id="88", agency_id="51"))
            configs = [amtrak_config(), GtfsFeedConfig("other", "Other Rail", "https://example.com/other.zip", zip_filename="other.zip")]
            _rows, _metadata, results = import_configured_feeds(root, station_id_for, download=False, configs=configs)
            route_uids = {route["route_uid"] for result in results for route in result.normalized["routes"]}
            self.assertIn("amtrak:88", route_uids)
            self.assertIn("other:88", route_uids)

    def test_shared_amtrak_source_keeps_sle_and_amtrak_products_separate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            sle_config = GtfsFeedConfig(
                "sle",
                "CTrail",
                "https://content.amtrak.com/content/gtfs/GTFS.zip",
                source_id="amtrak_official",
                zip_filename="GTFS.zip",
                route_filter=RouteFilter(include_agency_ids={"1230"}),
                default_service_name="Shore Line East",
                default_route_name="Shore Line East",
            )
            rows, metadata, results = import_configured_feeds(root, station_id_for, download=False, configs=[sle_config, amtrak_config()])
            self.assertEqual({item["source_id"] for item in metadata}, {"amtrak_official"})
            self.assertEqual(sum(1 for row in rows if row["train_number"] == "1633"), 2)
            self.assertTrue(all(row["agency"] == "CTrail" for row in rows if row["train_number"] == "1633"))
            self.assertFalse(any(row["agency"] == "Amtrak" and row["train_number"] == "1633" for row in rows))
            self.assertEqual({result.feed_id for result in results}, {"sle", "amtrak"})

    def test_amtrak_refresh_preserves_other_operator_normalized_data(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            other_config = GtfsFeedConfig("other", "Other Rail", "https://example.com/other.zip", zip_filename="other.zip")
            write_gtfs_zip(root, "other", "other.zip", base_files())
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", amtrak_files())
            import_configured_feeds(root, station_id_for, download=False, configs=[other_config, amtrak_config()])
            other_routes = root / "supporting_files" / "extraction" / "normalized_gtfs" / "other" / "routes.csv"
            before = other_routes.read_text()
            write_gtfs_zip(root, "amtrak_official", "GTFS.zip", {"agency.txt": amtrak_files()["agency.txt"]})
            _rows, metadata, _results = import_configured_feeds(root, station_id_for, download=False, configs=[amtrak_config()])
            self.assertEqual(other_routes.read_text(), before)
            self.assertEqual(metadata[0]["success"], "false")

    def test_calendar_dates_additions_and_removals(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files()
            files["calendar.txt"][0].update({"monday": "0", "tuesday": "0", "wednesday": "0", "thursday": "0", "friday": "0", "start_date": "20260720", "end_date": "20260724"})
            files["calendar_dates.txt"] = [
                {"service_id": "S1", "date": "20260721", "exception_type": "1"},
                {"service_id": "S1", "date": "20260722", "exception_type": "1"},
                {"service_id": "S1", "date": "20260722", "exception_type": "2"},
            ]
            write_gtfs_zip(root, "cal", "cal.zip", files)
            result = import_feed(root, GtfsFeedConfig("cal", "Cal Rail", "https://example.com/cal.zip", zip_filename="cal.zip"), station_id_for, download=False)
            self.assertEqual(result.rows[0]["service_dates"], "2026-07-21")

    def test_after_midnight_time(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files()
            files["stop_times.txt"][1]["arrival_time"] = "24:05:00"
            files["stop_times.txt"][1]["departure_time"] = "24:05:00"
            write_gtfs_zip(root, "late", "late.zip", files)
            result = import_feed(root, GtfsFeedConfig("late", "Late Rail", "https://example.com/late.zip", zip_filename="late.zip"), station_id_for, download=False)
            self.assertEqual(result.rows[1]["arrival_time"], "24:05")

    def test_feed_refresh_and_failed_import_preserves_existing_normalized_data(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = GtfsFeedConfig("refresh", "Refresh Rail", "https://example.com/refresh.zip", zip_filename="refresh.zip")
            write_gtfs_zip(root, "refresh", "refresh.zip", base_files())
            import_configured_feeds(root, station_id_for, download=False, configs=[config])
            routes_path = root / "supporting_files" / "extraction" / "normalized_gtfs" / "refresh" / "routes.csv"
            before = routes_path.read_text()
            write_gtfs_zip(root, "refresh", "refresh.zip", {"agency.txt": base_files()["agency.txt"]})
            _rows, metadata, _results = import_configured_feeds(root, station_id_for, download=False, configs=[config])
            self.assertEqual(routes_path.read_text(), before)
            self.assertEqual(metadata[0]["success"], "false")

    def test_multiple_source_stops_can_map_to_one_canonical_station(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files()
            files["stops.txt"][1]["stop_name"] = "New Haven Union Station"
            write_gtfs_zip(root, "canon", "canon.zip", files)
            config = GtfsFeedConfig("canon", "Canon Rail", "https://example.com/canon.zip", zip_filename="canon.zip")
            result = import_feed(root, config, station_id_for, download=False)
            self.assertEqual({row["canonical_station_id"] for row in result.normalized["stops"]}, {"GCT", "NHV"})
            self.assertEqual(len(result.normalized["stops"]), 2)

    def test_missing_optional_files_warns_without_abort(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files()
            files.pop("calendar_dates.txt")
            write_gtfs_zip(root, "optional", "optional.zip", files)
            result = import_feed(root, GtfsFeedConfig("optional", "Optional Rail", "https://example.com/optional.zip", zip_filename="optional.zip"), station_id_for, download=False)
            self.assertFalse(result.errors)
            self.assertTrue(any("Missing optional GTFS file" in warning for warning in result.warnings))

    def test_duplicate_identifier_warning(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = base_files()
            files["routes.txt"].append(dict(files["routes.txt"][0]))
            write_gtfs_zip(root, "dup", "dup.zip", files)
            result = import_feed(root, GtfsFeedConfig("dup", "Dup Rail", "https://example.com/dup.zip", zip_filename="dup.zip"), station_id_for, download=False)
            self.assertTrue(any("Duplicate route_id" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
