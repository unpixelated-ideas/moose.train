"""NJ Transit commuter rail scope, station identities, and source validation."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from gtfs_importer import GtfsFeedConfig, GtfsImportResult, RouteFilter

RAIL_URL = "https://www.njtransit.com/rail_data.zip"
ROUTES = {
    "1": "Atlantic City Rail Line",
    "2": "Montclair-Boonton Line",
    "3": "Montclair-Boonton Line",
    "5": "Main/Bergen County Line",
    "6": "Port Jervis Line",
    "7": "Morris & Essex Line",
    "8": "Gladstone Branch",
    "9": "Meadowlands Rail Line",
    "10": "Northeast Corridor",
    "11": "North Jersey Coast Line",
    "12": "North Jersey Coast Line",
    "14": "Pascack Valley Line",
    "15": "Princeton Shuttle",
    "16": "Raritan Valley Line",
}
REQUIRED_SERVICES = frozenset(ROUTES.values()) - {"Meadowlands Rail Line"}
STATIONS_PATH = Path(__file__).resolve().parents[1] / "reference/njt_stations.json"


def station_mappings():
    return json.loads(STATIONS_PATH.read_text(encoding="utf-8"))


def njt_feed_config(today: dt.date | None = None) -> GtfsFeedConfig:
    stations = station_mappings()
    return GtfsFeedConfig(
        feed_id="njt", operator_name="NJ Transit", url=RAIL_URL,
        zip_filename="rail_data.zip",
        route_filter=RouteFilter(include_route_ids=set(ROUTES), include_route_types={"2"}),
        route_service_names=ROUTES, route_names=ROUTES,
        stop_id_station_names={key: value["station_name"] for key, value in stations.items()},
        stop_name_aliases={value["source_name"]: value["station_name"] for value in stations.values()},
        station_id_map={value["station_name"]: value["station_id"] for value in stations.values()},
        train_number_fields=("block_id", "trip_short_name", "trip_id"),
        # The feed includes substitute buses on the Port Jervis and Gladstone rail routes.
        exclude_block_ids={"PJBUS"},
        exclude_block_id_pattern=r"GBUS[0-9]+",
        exclude_stop_ids={"1"},  # Philadelphia 30th Street is outside the expansion area.
        expected_stop_names={key: value["source_name"] for key, value in stations.items()},
        validate_output=lambda normalized, rows: validate_njt_output(normalized, rows, today),
    )


def validate_njt_result(result: GtfsImportResult, today: dt.date | None = None) -> None:
    """Fail closed on source changes requiring review before generating schedule assets."""
    if result.errors:
        raise ValueError("NJ Transit import failed: " + "; ".join(result.errors))
    validate_njt_output(result.normalized, result.rows, today)


def validate_njt_output(normalized, rows, today: dt.date | None = None):
    today = today or dt.datetime.now(ZoneInfo("America/New_York")).date()
    routes = {row["source_route_id"]: row for row in normalized["routes"]}
    for route_id, route in routes.items():
        if route["route_long_name"] != ROUTES[route_id]:
            raise ValueError(f"NJ Transit route {route_id} changed; review route selection")
    stations = station_mappings()
    for stop in normalized["stops"]:
        source_id = stop["source_stop_id"]
        if source_id not in stations:
            raise ValueError(f"Unmapped NJ Transit stop: {source_id}")
        if stop["canonical_station_id"] != stations[source_id]["station_id"]:
            raise ValueError(f"Incorrect NJ Transit station identity: {source_id}")
    current = dict.fromkeys(REQUIRED_SERVICES, False)
    directions = {name: set() for name in REQUIRED_SERVICES}
    for row in rows:
        if row["service_dates"]:
            active = any(dt.date.fromisoformat(day) >= today for day in row["service_dates"].split(","))
        else:
            active = dt.date.fromisoformat(row["service_end_date"]) >= today
        if row["service_name"] in current:
            current[row["service_name"]] |= active
    for trip in normalized["trips"]:
        if not trip["block_id"]:
            raise ValueError("NJ Transit trip has no published train number in block_id")
        if not trip["block_id"].isdigit():
            raise ValueError("Unrecognized NJ Transit train number; review possible replacement bus")
        if trip["service_name"] in directions:
            directions[trip["service_name"]].add(trip["direction_id"])
    missing = sorted(name for name, active in current.items() if not active)
    if missing:
        raise ValueError("NJ Transit has missing or expired service: " + ", ".join(missing))
    if any(value != {"0", "1"} for value in directions.values()):
        raise ValueError("NJ Transit must include both directions on every configured line")

