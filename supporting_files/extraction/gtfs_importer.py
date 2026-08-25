#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


REQUIRED_FILES = {
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "stops.txt",
}
OPTIONAL_FILES = {
    "calendar.txt",
    "calendar_dates.txt",
    "shapes.txt",
    "transfers.txt",
    "feed_info.txt",
}

NORMALIZED_TABLES = {
    "feeds": ["feed_id", "source_id", "operator_name", "source_url", "zip_path", "imported_at", "timezone"],
    "agencies": ["feed_id", "agency_uid", "source_agency_id", "agency_name", "agency_url", "agency_timezone"],
    "routes": ["feed_id", "route_uid", "source_route_id", "agency_uid", "source_agency_id", "route_short_name", "route_long_name", "route_type", "service_name", "route_name"],
    "trips": ["feed_id", "trip_uid", "source_trip_id", "route_uid", "source_route_id", "service_uid", "source_service_id", "trip_headsign", "trip_short_name", "direction_id", "block_id", "shape_uid", "source_shape_id", "operator_name", "service_name", "route_name"],
    "stops": ["feed_id", "stop_uid", "source_stop_id", "canonical_station_id", "stop_code", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station_uid", "source_parent_station", "in_search_scope"],
    "stop_times": ["feed_id", "trip_uid", "source_trip_id", "stop_uid", "source_stop_id", "arrival_time", "departure_time", "stop_sequence", "pickup_type", "drop_off_type", "note_id"],
    "calendars": ["feed_id", "service_uid", "source_service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
    "calendar_dates": ["feed_id", "service_uid", "source_service_id", "date", "exception_type"],
    "shapes": ["feed_id", "shape_uid", "source_shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"],
    "transfers": ["feed_id", "from_stop_uid", "source_from_stop_id", "to_stop_uid", "source_to_stop_id", "transfer_type", "min_transfer_time"],
    "canonical_stations": ["canonical_station_id", "station_name"],
}

AMTRAK_OFFICIAL_URL = "https://content.amtrak.com/content/gtfs/GTFS.zip"
AMTRAK_SOURCE_ID = "amtrak_official"
AMTRAK_SCOPE_STOP_IDS = {
    "BER",  # Berlin, CT
    "BRP",  # Bridgeport, CT
    "HFD",  # Hartford, CT
    "MDN",  # Meriden, CT
    "MYS",  # Mystic, CT
    "NHV",  # New Haven Union Station
    "NLC",  # New London, CT
    "NYP",  # New York Penn
    "OSB",  # Old Saybrook, CT
    "SPG",  # Springfield, MA
    "STM",  # Stamford, CT
    "STS",  # New Haven State Street
    "WFD",  # Wallingford, CT
    "WLY",  # Westerly, RI
    "WND",  # Windsor, CT
    "WNL",  # Windsor Locks, CT
}

AMTRAK_STOP_ALIASES = {
    "Berlin Amtrak": "Berlin",
    "Bridgeport Amtrak Station": "Bridgeport",
    "Hartford Amtrak Station": "Hartford",
    "Mystic Amtrak": "Mystic",
    "New Haven": "New Haven Union Station",
    "New London": "New London",
    "Ny Moynihan Train Hall At Penn Station": "New York Penn",
    "Old Saybrook Amtrak Station": "Old Saybrook",
    "Springfield": "Springfield",
    "Stamford Amtrak Station": "Stamford",
    "Wallingford Amtrak": "Wallingford",
    "Westerly Amtrak Station": "Westerly",
}


@dataclass(frozen=True)
class RouteFilter:
    include_route_ids: set[str] = field(default_factory=set)
    exclude_route_ids: set[str] = field(default_factory=set)
    include_agency_ids: set[str] = field(default_factory=set)
    exclude_agency_ids: set[str] = field(default_factory=set)
    include_route_long_names: set[str] = field(default_factory=set)
    include_route_types: set[str] = field(default_factory=set)

    def allows(self, route: dict[str, str]) -> bool:
        route_id = route.get("route_id", "")
        agency_id = route.get("agency_id", "")
        long_name = route.get("route_long_name", "")
        if self.include_route_ids and route_id not in self.include_route_ids:
            return False
        if self.include_agency_ids and agency_id not in self.include_agency_ids:
            return False
        if self.include_route_long_names and long_name not in self.include_route_long_names:
            return False
        if self.include_route_types and route.get("route_type", "") not in self.include_route_types:
            return False
        if route_id in self.exclude_route_ids:
            return False
        if agency_id in self.exclude_agency_ids:
            return False
        return True


@dataclass(frozen=True)
class GtfsFeedConfig:
    feed_id: str
    operator_name: str
    url: str
    enabled: bool = True
    source_id: str = ""
    zip_filename: str = ""
    route_filter: RouteFilter = field(default_factory=RouteFilter)
    route_service_names: dict[str, str] = field(default_factory=dict)
    route_names: dict[str, str] = field(default_factory=dict)
    stop_name_aliases: dict[str, str] = field(default_factory=dict)
    stop_id_station_names: dict[str, str] = field(default_factory=dict)
    exclude_stop_ids: set[str] = field(default_factory=set)
    in_scope_stop_ids: set[str] = field(default_factory=set)
    min_in_scope_stops: int = 0
    emit_only_in_scope_stops: bool = False
    station_id_map: dict[str, str] = field(default_factory=dict)
    default_service_name: str = ""
    default_route_name: str = ""

    def zip_name(self) -> str:
        return self.zip_filename or f"{self.feed_id}.zip"

    def source_key(self) -> str:
        return self.source_id or self.feed_id


@dataclass
class GtfsImportResult:
    feed_id: str
    source_name: str
    rows: list[dict[str, str]]
    normalized: dict[str, list[dict[str, str]]]
    metadata: dict[str, str]
    warnings: list[str]
    errors: list[str]


def default_feed_configs() -> list[GtfsFeedConfig]:
    return [
        GtfsFeedConfig(
            feed_id="mnr",
            operator_name="Metro-North",
            url="https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip",
            zip_filename="gtfsmnr.zip",
            route_filter=RouteFilter(include_route_ids={"3", "4", "5", "6"}),
            route_service_names={
                "3": "New Haven Line",
                "4": "New Canaan Branch",
                "5": "Danbury Branch",
                "6": "Waterbury Branch",
            },
            route_names={
                "3": "New Haven Line",
                "4": "New Haven Line - New Canaan Branch",
                "5": "New Haven Line - Danbury Branch",
                "6": "New Haven Line - Waterbury Branch",
            },
            stop_name_aliases={
                "Harlem-125 St": "Harlem-125th St.",
                "Mt Vernon East": "Mount Vernon East",
                "New Haven": "New Haven Union Station",
                "New Haven-State St": "New Haven State Street",
            },
            exclude_stop_ids={"651"},
        ),
        GtfsFeedConfig(
            feed_id="hartford",
            operator_name="CTrail",
            url="https://ctrides.com/hlgtfs.zip",
            zip_filename="hlgtfs.zip",
            default_service_name="Hartford Line",
            default_route_name="Hartford Line",
            stop_name_aliases={
                "BERLIN": "Berlin",
                "HARTFORD": "Hartford",
                "MERIDEN": "Meriden",
                "NEW HAVEN UNION STATION": "New Haven Union Station",
                "SPRINGFIELD": "Springfield",
                "STATE STREET STATION": "New Haven State Street",
                "WALLINGFORD": "Wallingford",
                "WINDSOR": "Windsor",
                "WINDSOR LOCKS": "Windsor Locks",
            },
        ),
        GtfsFeedConfig(
            feed_id="sle",
            operator_name="CTrail",
            url=AMTRAK_OFFICIAL_URL,
            source_id=AMTRAK_SOURCE_ID,
            zip_filename="GTFS.zip",
            route_filter=RouteFilter(include_agency_ids={"1230"}),
            default_service_name="Shore Line East",
            default_route_name="Shore Line East",
            stop_name_aliases={
                "Bridgeport Amtrak Station": "Bridgeport",
                "New Haven, CT - Union Station": "New Haven Union Station",
                "New Haven, CT - State Street Station": "New Haven State Street",
                "Old Saybrook Amtrak Station": "Old Saybrook",
                "Stamford Amtrak Station": "Stamford",
            },
        ),
        GtfsFeedConfig(
            feed_id="amtrak",
            operator_name="Amtrak",
            url=AMTRAK_OFFICIAL_URL,
            source_id=AMTRAK_SOURCE_ID,
            zip_filename="GTFS.zip",
            route_filter=RouteFilter(include_agency_ids={"51"}, include_route_types={"2"}),
            in_scope_stop_ids=AMTRAK_SCOPE_STOP_IDS,
            min_in_scope_stops=2,
            emit_only_in_scope_stops=True,
            stop_name_aliases=AMTRAK_STOP_ALIASES,
            stop_id_station_names={
                "BER": "Berlin",
                "BRP": "Bridgeport",
                "HFD": "Hartford",
                "MDN": "Meriden",
                "MYS": "Mystic",
                "NHV": "New Haven Union Station",
                "NLC": "New London",
                "NYP": "New York Penn",
                "OSB": "Old Saybrook",
                "SPG": "Springfield",
                "STM": "Stamford",
                "STS": "New Haven State Street",
                "WFD": "Wallingford",
                "WLY": "Westerly",
                "WND": "Windsor",
                "WNL": "Windsor Locks",
            },
        ),
    ]


def import_configured_feeds(
    root: Path,
    station_id_for: Callable[[str], str],
    *,
    download: bool = True,
    configs: list[GtfsFeedConfig] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[GtfsImportResult]]:
    results = []
    all_rows = []
    metadata = []
    normalized_root = root / "supporting_files" / "extraction" / "normalized_gtfs"
    metadata_root = root / "supporting_files" / "extraction"
    downloaded_sources = set()
    for config in configs or default_feed_configs():
        if not config.enabled:
            continue
        should_download = download and config.source_key() not in downloaded_sources
        result = import_feed(root, config, station_id_for, download=should_download)
        if not result.errors:
            downloaded_sources.add(config.source_key())
        results.append(result)
        metadata.append(result.metadata)
        if result.errors:
            continue
        all_rows.extend(result.rows)
        replace_normalized_feed(normalized_root, result)
    write_csv(metadata_root / "gtfs_import_metadata.csv", IMPORT_METADATA_COLUMNS, metadata)
    return all_rows, metadata, results


IMPORT_METADATA_COLUMNS = [
    "feed_id",
    "source_id",
    "operator_name",
    "source_url",
    "source_name",
    "imported_at",
    "success",
    "record_counts",
    "warnings",
    "errors",
]


def import_feed(root: Path, config: GtfsFeedConfig, station_id_for: Callable[[str], str], *, download: bool = True) -> GtfsImportResult:
    imported_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    source_dir = root / "supporting_files" / "source_gtfs" / config.source_key()
    zip_path = source_dir / config.zip_name()
    feed_dir = source_dir / "feed"
    warnings: list[str] = []
    errors: list[str] = []
    try:
        if download or not zip_path.exists():
            download_zip(config.url, zip_path)
        validate_zip(zip_path)
        with tempfile.TemporaryDirectory(prefix=f"{config.feed_id}_gtfs_") as tmp:
            tmp_feed = Path(tmp) / "feed"
            unzip_feed(zip_path, tmp_feed)
            validate_required_files(tmp_feed)
            tables = read_gtfs_tables(tmp_feed, warnings)
            normalized, rows, source_name = normalize_feed(config, zip_path, tables, imported_at, station_id_for, warnings)
            replace_feed_dir(feed_dir, tmp_feed)
    except Exception as exc:
        errors.append(str(exc))
        normalized = {name: [] for name in NORMALIZED_TABLES}
        rows = []
        source_name = f"{config.feed_id}_gtfs_failed.zip"
    metadata = {
        "feed_id": config.feed_id,
        "source_id": config.source_key(),
        "operator_name": config.operator_name,
        "source_url": config.url,
        "source_name": source_name,
        "imported_at": imported_at,
        "success": "false" if errors else "true",
        "record_counts": json.dumps({name: len(items) for name, items in normalized.items()}, sort_keys=True),
        "warnings": json.dumps(warnings, sort_keys=True),
        "errors": json.dumps(errors, sort_keys=True),
    }
    return GtfsImportResult(config.feed_id, source_name, rows, normalized, metadata, warnings, errors)


def download_zip(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        urllib.request.urlretrieve(url, tmp_path)
        validate_zip(tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def validate_zip(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing GTFS zip: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Invalid GTFS zip: {path}")
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Invalid file in GTFS zip {path}: {bad}")


def unzip_feed(zip_path: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target)


def validate_required_files(feed_dir: Path) -> None:
    missing = sorted(name for name in REQUIRED_FILES if not (feed_dir / name).exists())
    if missing:
        raise FileNotFoundError(f"Missing required GTFS files: {', '.join(missing)}")
    if not (feed_dir / "calendar.txt").exists() and not (feed_dir / "calendar_dates.txt").exists():
        raise FileNotFoundError("GTFS feed must include calendar.txt, calendar_dates.txt, or both")


def read_gtfs_tables(feed_dir: Path, warnings: list[str]) -> dict[str, list[dict[str, str]]]:
    tables = {}
    for filename in sorted(REQUIRED_FILES | OPTIONAL_FILES):
        path = feed_dir / filename
        if not path.exists():
            if filename in OPTIONAL_FILES:
                warnings.append(f"Missing optional GTFS file: {filename}")
                tables[filename] = []
                continue
            raise FileNotFoundError(f"Missing required GTFS file: {filename}")
        tables[filename] = read_csv(path)
    return tables


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        try:
            return list(csv.DictReader(fh))
        except csv.Error as exc:
            raise ValueError(f"Malformed CSV {path.name}: {exc}") from exc


def normalize_feed(
    config: GtfsFeedConfig,
    zip_path: Path,
    tables: dict[str, list[dict[str, str]]],
    imported_at: str,
    station_id_for: Callable[[str], str],
    warnings: list[str],
) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]], str]:
    warn_duplicate_ids(tables["agency.txt"], "agency_id", "agency.txt", warnings)
    warn_duplicate_ids(tables["routes.txt"], "route_id", "routes.txt", warnings)
    warn_duplicate_ids(tables["trips.txt"], "trip_id", "trips.txt", warnings)
    warn_duplicate_ids(tables["stops.txt"], "stop_id", "stops.txt", warnings)
    warn_duplicate_ids(tables["calendar.txt"], "service_id", "calendar.txt", warnings)
    agencies_by_id = {row.get("agency_id", ""): row for row in tables["agency.txt"]}
    included_routes = {
        row["route_id"]: row
        for row in tables["routes.txt"]
        if config.route_filter.allows(row)
    }
    if config.route_filter.include_route_types:
        route_ids = {row.get("route_id", "") for row in tables["routes.txt"]}
        non_rail_route_ids = {
            row.get("route_id", "") for row in tables["routes.txt"]
            if row.get("route_id", "") in route_ids and row.get("route_type", "") not in config.route_filter.include_route_types
        }
        excluded_non_rail_trips = sum(1 for row in tables["trips.txt"] if row.get("route_id") in non_rail_route_ids)
        if excluded_non_rail_trips:
            warnings.append(f"Excluded {excluded_non_rail_trips} trips on route_type outside configured scope: {', '.join(sorted(config.route_filter.include_route_types))}")
    trips = [row for row in tables["trips.txt"] if row.get("route_id") in included_routes]
    trip_ids = {row["trip_id"] for row in trips}
    stop_times = [
        row for row in tables["stop_times.txt"]
        if row.get("trip_id") in trip_ids and row.get("stop_id") not in config.exclude_stop_ids
    ]
    if config.min_in_scope_stops:
        in_scope_by_trip: dict[str, set[str]] = {}
        for row in stop_times:
            if row.get("stop_id") in config.in_scope_stop_ids:
                in_scope_by_trip.setdefault(row["trip_id"], set()).add(row["stop_id"])
        eligible_trip_ids = {
            trip_id for trip_id, stop_ids_for_trip in in_scope_by_trip.items()
            if len(stop_ids_for_trip) >= config.min_in_scope_stops
        }
        excluded_trip_count = len(trips) - len(eligible_trip_ids)
        if excluded_trip_count:
            warnings.append(f"Excluded {excluded_trip_count} trips with fewer than {config.min_in_scope_stops} in-scope stops")
        trips = [row for row in trips if row["trip_id"] in eligible_trip_ids]
        trip_ids = {row["trip_id"] for row in trips}
        stop_times = [row for row in stop_times if row.get("trip_id") in trip_ids]
    used_route_ids = {row["route_id"] for row in trips}
    included_routes = {route_id: row for route_id, row in included_routes.items() if route_id in used_route_ids}
    service_ids = {row["service_id"] for row in trips}
    stop_ids = {row["stop_id"] for row in stop_times}
    excluded_stop_count = sum(
        1 for row in tables["stop_times.txt"]
        if row.get("trip_id") in trip_ids and row.get("stop_id") in config.exclude_stop_ids
    )
    if excluded_stop_count:
        warnings.append(f"Excluded {excluded_stop_count} stop_times for configured non-public stop_ids: {', '.join(sorted(config.exclude_stop_ids))}")
    stops_by_id = {row["stop_id"]: row for row in tables["stops.txt"]}
    calendars = [row for row in tables["calendar.txt"] if row.get("service_id") in service_ids]
    calendar_dates = [row for row in tables["calendar_dates.txt"] if row.get("service_id") in service_ids]
    shapes = [row for row in tables["shapes.txt"] if row.get("shape_id") in {trip.get("shape_id", "") for trip in trips}]
    transfers = [
        row for row in tables["transfers.txt"]
        if row.get("from_stop_id") in stop_ids and row.get("to_stop_id") in stop_ids
    ]

    validate_foreign_keys(included_routes, trips, stop_times, stops_by_id, calendars, calendar_dates, warnings)
    service_summaries = summarize_services(calendars, calendar_dates, warnings)
    source_name = source_name_for(config, zip_path, tables, service_summaries)
    timezone = feed_timezone(agencies_by_id)

    normalized = {name: [] for name in NORMALIZED_TABLES}
    normalized["feeds"].append({
        "feed_id": config.feed_id,
        "source_id": config.source_key(),
        "operator_name": config.operator_name,
        "source_url": config.url,
        "zip_path": str(zip_path),
        "imported_at": imported_at,
        "timezone": timezone,
    })
    for row in tables["agency.txt"]:
        normalized["agencies"].append({
            "feed_id": config.feed_id,
            "agency_uid": uid(config.feed_id, row.get("agency_id", "")),
            "source_agency_id": row.get("agency_id", ""),
            "agency_name": row.get("agency_name", ""),
            "agency_url": row.get("agency_url", ""),
            "agency_timezone": row.get("agency_timezone", ""),
        })
    for row in included_routes.values():
        route_id = row["route_id"]
        normalized["routes"].append({
            "feed_id": config.feed_id,
            "route_uid": uid(config.feed_id, route_id),
            "source_route_id": route_id,
            "agency_uid": uid(config.feed_id, row.get("agency_id", "")),
            "source_agency_id": row.get("agency_id", ""),
            "route_short_name": row.get("route_short_name", ""),
            "route_long_name": row.get("route_long_name", ""),
            "route_type": row.get("route_type", ""),
            "service_name": service_name_for(config, row),
            "route_name": route_name_for(config, row),
        })
    for row in trips:
        route = included_routes[row["route_id"]]
        normalized["trips"].append({
            "feed_id": config.feed_id,
            "trip_uid": uid(config.feed_id, row["trip_id"]),
            "source_trip_id": row["trip_id"],
            "route_uid": uid(config.feed_id, row["route_id"]),
            "source_route_id": row["route_id"],
            "service_uid": uid(config.feed_id, row["service_id"]),
            "source_service_id": row["service_id"],
            "trip_headsign": row.get("trip_headsign", ""),
            "trip_short_name": row.get("trip_short_name", ""),
            "direction_id": row.get("direction_id", ""),
            "block_id": row.get("block_id", ""),
            "shape_uid": uid(config.feed_id, row.get("shape_id", "")) if row.get("shape_id") else "",
            "source_shape_id": row.get("shape_id", ""),
            "operator_name": config.operator_name,
            "service_name": service_name_for(config, route),
            "route_name": route_name_for(config, route),
        })
    canonical = {}
    for stop_id in stop_ids:
        stop = stops_by_id.get(stop_id)
        if not stop:
            continue
        stop_name = canonical_stop_name(config, stop.get("stop_name", ""), stop_id)
        canonical_id = canonical_station_id(config, stop_name, station_id_for)
        canonical[canonical_id] = stop_name
        parent = stop.get("parent_station", "")
        normalized["stops"].append({
            "feed_id": config.feed_id,
            "stop_uid": uid(config.feed_id, stop_id),
            "source_stop_id": stop_id,
            "canonical_station_id": canonical_id,
            "stop_code": stop.get("stop_code", ""),
            "stop_name": stop_name,
            "stop_lat": stop.get("stop_lat", ""),
            "stop_lon": stop.get("stop_lon", ""),
            "location_type": stop.get("location_type", ""),
            "parent_station_uid": uid(config.feed_id, parent) if parent else "",
            "source_parent_station": parent,
            "in_search_scope": "true" if in_search_scope(config, stop_id) else "false",
        })
    normalized["canonical_stations"] = [
        {"canonical_station_id": station_id, "station_name": station_name}
        for station_id, station_name in sorted(canonical.items())
    ]
    for row in stop_times:
        validate_gtfs_time(row.get("arrival_time", ""), warnings)
        validate_gtfs_time(row.get("departure_time", ""), warnings)
        normalized["stop_times"].append({
            "feed_id": config.feed_id,
            "trip_uid": uid(config.feed_id, row["trip_id"]),
            "source_trip_id": row["trip_id"],
            "stop_uid": uid(config.feed_id, row["stop_id"]),
            "source_stop_id": row["stop_id"],
            "arrival_time": row.get("arrival_time", ""),
            "departure_time": row.get("departure_time", ""),
            "stop_sequence": row.get("stop_sequence", ""),
            "pickup_type": row.get("pickup_type", ""),
            "drop_off_type": row.get("drop_off_type", ""),
            "note_id": row.get("note_id", ""),
        })
    for row in calendars:
        normalized["calendars"].append({
            "feed_id": config.feed_id,
            "service_uid": uid(config.feed_id, row["service_id"]),
            "source_service_id": row["service_id"],
            "monday": row.get("monday", ""),
            "tuesday": row.get("tuesday", ""),
            "wednesday": row.get("wednesday", ""),
            "thursday": row.get("thursday", ""),
            "friday": row.get("friday", ""),
            "saturday": row.get("saturday", ""),
            "sunday": row.get("sunday", ""),
            "start_date": gtfs_date_to_iso(row.get("start_date", "")),
            "end_date": gtfs_date_to_iso(row.get("end_date", "")),
        })
    for row in calendar_dates:
        normalized["calendar_dates"].append({
            "feed_id": config.feed_id,
            "service_uid": uid(config.feed_id, row["service_id"]),
            "source_service_id": row["service_id"],
            "date": gtfs_date_to_iso(row.get("date", "")),
            "exception_type": row.get("exception_type", ""),
        })
    for row in shapes:
        normalized["shapes"].append({
            "feed_id": config.feed_id,
            "shape_uid": uid(config.feed_id, row.get("shape_id", "")),
            "source_shape_id": row.get("shape_id", ""),
            "shape_pt_lat": row.get("shape_pt_lat", ""),
            "shape_pt_lon": row.get("shape_pt_lon", ""),
            "shape_pt_sequence": row.get("shape_pt_sequence", ""),
            "shape_dist_traveled": row.get("shape_dist_traveled", ""),
        })
    for row in transfers:
        normalized["transfers"].append({
            "feed_id": config.feed_id,
            "from_stop_uid": uid(config.feed_id, row.get("from_stop_id", "")),
            "source_from_stop_id": row.get("from_stop_id", ""),
            "to_stop_uid": uid(config.feed_id, row.get("to_stop_id", "")),
            "source_to_stop_id": row.get("to_stop_id", ""),
            "transfer_type": row.get("transfer_type", ""),
            "min_transfer_time": row.get("min_transfer_time", ""),
        })
    rows = derive_stop_event_rows(config, included_routes, trips, stop_times, stops_by_id, service_summaries, source_name, zip_path, station_id_for)
    return normalized, rows, source_name


def validate_foreign_keys(routes, trips, stop_times, stops_by_id, calendars, calendar_dates, warnings) -> None:
    route_ids = set(routes)
    for trip in trips:
        if trip.get("route_id") not in route_ids:
            warnings.append(f"Trip references excluded or missing route_id: {trip.get('trip_id')}")
    for item in stop_times:
        if item.get("stop_id") not in stops_by_id:
            warnings.append(f"Stop time references missing stop_id: {item.get('stop_id')}")
    calendar_services = {row.get("service_id") for row in calendars} | {row.get("service_id") for row in calendar_dates}
    for trip in trips:
        if trip.get("service_id") not in calendar_services:
            warnings.append(f"Trip references missing service_id: {trip.get('trip_id')} -> {trip.get('service_id')}")


def warn_duplicate_ids(rows: list[dict[str, str]], column: str, table_name: str, warnings: list[str]) -> None:
    seen = set()
    duplicates = set()
    for row in rows:
        value = row.get(column, "")
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    for value in sorted(duplicates):
        warnings.append(f"Duplicate {column} in {table_name}: {value}")


def derive_stop_event_rows(config, routes, trips, stop_times, stops_by_id, service_summaries, source_name, zip_path, station_id_for):
    by_trip: dict[str, list[dict[str, str]]] = {}
    for row in stop_times:
        by_trip.setdefault(row["trip_id"], []).append(row)
    rows = []
    for trip in trips:
        calendar = service_summaries.get(trip["service_id"])
        if not calendar:
            continue
        route = routes[trip["route_id"]]
        direction = direction_for(config, trip)
        ordered_stop_times = sorted(by_trip.get(trip["trip_id"], []), key=lambda row: int(row["stop_sequence"]))
        raw_notes = raw_notes_for(config, trip, ordered_stop_times, stops_by_id)
        for sequence, item in enumerate(ordered_stop_times, start=1):
            if config.emit_only_in_scope_stops and not in_search_scope(config, item["stop_id"]):
                continue
            stop = stops_by_id[item["stop_id"]]
            station_name = canonical_stop_name(config, stop.get("stop_name", ""), item["stop_id"])
            rows.append({
                "agency": config.operator_name,
                "service_name": service_name_for(config, route),
                "route_name": route_name_for(config, route),
                "train_number": trip.get("trip_short_name") or trip["trip_id"],
                "direction": direction,
                "station_id": canonical_station_id(config, station_name, station_id_for),
                "station_name": station_name,
                "station_sequence": item.get("stop_sequence") or str(sequence),
                "arrival_time": trim_gtfs_time(item.get("arrival_time", "")),
                "departure_time": trim_gtfs_time(item.get("departure_time", "")),
                "service_start_date": calendar["start"],
                "service_end_date": calendar["end"],
                "service_dates": calendar["service_dates"],
                "service_days": calendar["service_days"],
                "timetable_effective_date": calendar["start"],
                "timetable_last_updated_date": dt.datetime.fromtimestamp(zip_path.stat().st_mtime).date().isoformat(),
                "timetable_revision_date": "",
                "source_original_filename": config.zip_name(),
                "source_pdf": source_name,
                "source_page": "0",
                "raw_notes": raw_notes,
            })
    return rows


def summarize_services(calendars: list[dict[str, str]], calendar_dates: list[dict[str, str]], warnings: list[str]) -> dict[str, dict[str, str]]:
    by_service = {row["service_id"]: row for row in calendars}
    exceptions: dict[str, dict[str, set[dt.date]]] = {}
    for row in calendar_dates:
        try:
            date = parse_gtfs_date(row["date"])
        except ValueError:
            warnings.append(f"Invalid calendar_dates date: {row}")
            continue
        bucket = exceptions.setdefault(row["service_id"], {"1": set(), "2": set()})
        bucket.setdefault(row.get("exception_type", ""), set()).add(date)
    service_ids = set(by_service) | set(exceptions)
    summaries = {}
    for service_id in service_ids:
        dates: set[dt.date] = set()
        calendar = by_service.get(service_id)
        if calendar:
            start = parse_gtfs_date(calendar["start_date"])
            end = parse_gtfs_date(calendar["end_date"])
            enabled = [calendar.get(day, "0") == "1" for day in WEEK_FIELDS]
            for offset in range((end - start).days + 1):
                date = start + dt.timedelta(days=offset)
                if enabled[date.weekday()]:
                    dates.add(date)
        dates |= exceptions.get(service_id, {}).get("1", set())
        dates -= exceptions.get(service_id, {}).get("2", set())
        if not dates:
            warnings.append(f"Service has no active dates: {service_id}")
            continue
        summaries[service_id] = summarize_date_set(dates)
    return summaries


WEEK_FIELDS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def summarize_date_set(dates: set[dt.date]) -> dict[str, str]:
    start = min(dates)
    end = max(dates)
    if len(dates) == 1:
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "service_days": "",
            "service_dates": start.isoformat(),
        }
    all_dates = {start + dt.timedelta(days=offset) for offset in range((end - start).days + 1)}
    patterns = {
        "weekday": {date for date in all_dates if date.weekday() < 5},
        "monday_through_thursday": {date for date in all_dates if date.weekday() <= 3},
        "friday": {date for date in all_dates if date.weekday() == 4},
        "saturday": {date for date in all_dates if date.weekday() == 5},
        "sunday": {date for date in all_dates if date.weekday() == 6},
        "weekend": {date for date in all_dates if date.weekday() >= 5},
    }
    service_days = next((name for name, pattern in patterns.items() if dates == pattern), "")
    if dates == all_dates:
        service_days = "daily"
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "service_days": service_days,
        "service_dates": "" if service_days else ",".join(date.isoformat() for date in sorted(dates)),
    }


def source_name_for(config, zip_path, tables, service_summaries) -> str:
    starts = [item["start"] for item in service_summaries.values()]
    feed_info = tables.get("feed_info.txt", [])
    version = feed_info[0].get("feed_version", "") if feed_info else ""
    updated = version if re.fullmatch(r"\d{8}", version) else dt.datetime.fromtimestamp(zip_path.stat().st_mtime).date().isoformat()
    if re.fullmatch(r"\d{8}", updated):
        updated = gtfs_date_to_iso(updated)
    return f"{config.feed_id}_gtfs_effective_{min(starts)}_updated_{updated}.zip"


def feed_timezone(agencies_by_id: dict[str, dict[str, str]]) -> str:
    zones = [row.get("agency_timezone", "") for row in agencies_by_id.values() if row.get("agency_timezone")]
    return zones[0] if zones else "America/New_York"


def uid(feed_id: str, source_id: str) -> str:
    return f"{feed_id}:{source_id}"


def service_name_for(config: GtfsFeedConfig, route: dict[str, str]) -> str:
    return config.route_service_names.get(route.get("route_id", "")) or config.default_service_name or route.get("route_long_name") or route.get("route_short_name") or config.operator_name


def route_name_for(config: GtfsFeedConfig, route: dict[str, str]) -> str:
    return config.route_names.get(route.get("route_id", "")) or config.default_route_name or route.get("route_long_name") or route.get("route_short_name") or service_name_for(config, route)


def canonical_stop_name(config: GtfsFeedConfig, name: str, stop_id: str = "") -> str:
    if stop_id and stop_id in config.stop_id_station_names:
        return config.stop_id_station_names[stop_id]
    clean = re.sub(r"\s+", " ", name).strip()
    return config.stop_name_aliases.get(clean, clean)


def canonical_station_id(config: GtfsFeedConfig, station_name: str, station_id_for: Callable[[str], str]) -> str:
    return config.station_id_map.get(station_name) or station_id_for(station_name)


def in_search_scope(config: GtfsFeedConfig, stop_id: str) -> bool:
    return not config.in_scope_stop_ids or stop_id in config.in_scope_stop_ids


def direction_for(config: GtfsFeedConfig, trip: dict[str, str]) -> str:
    headsign = re.sub(r"\s*\(Bus\)\s*$", "", trip.get("trip_headsign", "")).strip()
    if headsign == "Grand Central":
        return "To Grand Central"
    if headsign:
        return f"To {canonical_stop_name(config, headsign)}"
    return config.default_route_name or config.operator_name


def raw_notes_for(config: GtfsFeedConfig, trip: dict[str, str], stop_times: list[dict[str, str]] | None = None, stops_by_id: dict[str, dict[str, str]] | None = None) -> str:
    notes = [direction_for(config, trip), "GTFS"]
    if "(Bus)" in trip.get("trip_headsign", ""):
        notes.append("Bus substitution")
    for key in ["peak_offpeak", "trip_id", "service_id"]:
        if trip.get(key):
            notes.append(f"gtfs_{key}={trip[key]}" if key in {"trip_id", "service_id"} else f"{key}={trip[key]}")
    if stop_times and stops_by_id:
        first = stops_by_id.get(stop_times[0].get("stop_id", ""), {})
        last = stops_by_id.get(stop_times[-1].get("stop_id", ""), {})
        if first.get("stop_name"):
            notes.append(f"source_origin={canonical_stop_name(config, first.get('stop_name', ''), stop_times[0].get('stop_id', ''))}")
        if last.get("stop_name"):
            notes.append(f"source_destination={canonical_stop_name(config, last.get('stop_name', ''), stop_times[-1].get('stop_id', ''))}")
    return "; ".join(notes)


def parse_gtfs_date(value: str) -> dt.date:
    if not re.fullmatch(r"\d{8}", value or ""):
        raise ValueError(f"Invalid GTFS date: {value}")
    return dt.date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def gtfs_date_to_iso(value: str) -> str:
    if not value:
        return ""
    date = parse_gtfs_date(value)
    return date.isoformat()


def validate_gtfs_time(value: str, warnings: list[str]) -> None:
    if not value:
        return
    if not re.fullmatch(r"\d{1,3}:\d{2}:\d{2}", value):
        warnings.append(f"Invalid GTFS time: {value}")
        return
    hour, minute, second = [int(part) for part in value.split(":")]
    if minute > 59 or second > 59:
        warnings.append(f"Invalid GTFS time: {value}")


def trim_gtfs_time(value: str) -> str:
    if not value:
        return ""
    hour, minute, _second = value.split(":")
    return f"{int(hour):02d}:{int(minute):02d}"


def replace_feed_dir(feed_dir: Path, tmp_feed: Path) -> None:
    feed_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = feed_dir.parent / f".{feed_dir.name}.next"
    if tmp_target.exists():
        shutil.rmtree(tmp_target)
    shutil.copytree(tmp_feed, tmp_target)
    if feed_dir.exists():
        shutil.rmtree(feed_dir)
    tmp_target.replace(feed_dir)


def replace_normalized_feed(root: Path, result: GtfsImportResult) -> None:
    target = root / result.feed_id
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix=f".{result.feed_id}.") as tmp:
        tmp_path = Path(tmp)
        for table_name, columns in NORMALIZED_TABLES.items():
            write_csv(tmp_path / f"{table_name}.csv", columns, result.normalized.get(table_name, []))
        next_path = root / f".{result.feed_id}.next"
        if next_path.exists():
            shutil.rmtree(next_path)
        shutil.copytree(tmp_path, next_path)
    if target.exists():
        shutil.rmtree(target)
    next_path.replace(target)


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in columns} for row in rows)
