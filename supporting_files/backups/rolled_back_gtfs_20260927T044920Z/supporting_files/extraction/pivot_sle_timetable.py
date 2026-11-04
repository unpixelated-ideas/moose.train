#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


DEFAULT_SOURCE = Path(__file__).resolve().parent / "source_csvs" / "ctrail_shore_line_east_effective_2026-03-29_updated_2026-03-17.csv"
INBOUND_STATION_ORDER = [
    "New London",
    "Old Saybrook",
    "Westbrook",
    "Clinton",
    "Madison",
    "Guilford",
    "Branford",
    "New Haven - State Street",
    "New Haven - Union Station",
    "New Haven Union Station",
]


def is_weekday_sle_service_table_row(row: dict[str, str]) -> bool:
    """Return true for public SLE/Amtrak service-table rows, not MNR connections."""
    return (
        row.get("direction") == "To New Haven"
        and row.get("service_days") == "weekday"
        and row.get("agency") in {"CTrail", "Amtrak"}
    )


def minutes(value: str) -> int:
    if not value or value == "unknown":
        return 10**9
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def display_train(row_key: tuple[str, str, str]) -> str:
    agency, _service, train_number = row_key
    prefix = "SLE" if agency == "CTrail" else agency
    return f"{prefix} {train_number}"


def display_time(row: dict[str, str]) -> str:
    arrival = row.get("arrival_time", "")
    departure = row.get("departure_time", "")
    if arrival and departure and arrival == departure:
        return arrival
    if arrival and departure:
        return f"{arrival}/{departure}"
    return arrival or departure


def pivot_rows(rows: list[dict[str, str]]) -> tuple[list[str], list[str], dict[tuple[str, str], str]]:
    selected = [row for row in rows if is_weekday_sle_service_table_row(row)]
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in selected:
        grouped[(row["agency"], row["service_name"], row["train_number"])].append(row)

    ordered_groups = []
    for key, group in grouped.items():
        group.sort(key=lambda row: int(row["station_sequence"]))
        first_row = next((row for row in group if row.get("departure_time") or row.get("arrival_time")), group[0])
        first_time = minutes(first_row.get("departure_time") or first_row.get("arrival_time", ""))
        ordered_groups.append((first_time, key, group))
    ordered_groups.sort(key=lambda item: (item[0], item[1][0], item[1][2]))

    seen_stations = []
    for _first_time, _key, group in ordered_groups:
        for row in group:
            station = row["station_name"]
            if station not in seen_stations:
                seen_stations.append(station)

    stations = [station for station in INBOUND_STATION_ORDER if station in seen_stations]
    stations.extend(station for station in seen_stations if station not in stations)

    trains = [display_train(key) for _first_time, key, _group in ordered_groups]
    cells: dict[tuple[str, str], str] = {}
    for _first_time, key, group in ordered_groups:
        train = display_train(key)
        by_station: dict[str, list[str]] = defaultdict(list)
        for row in group:
            by_station[row["station_name"]].append(display_time(row))
        for station, values in by_station.items():
            cells[(station, train)] = "<br>".join(values)
    return stations, trains, cells


def write_markdown_table(stations: list[str], trains: list[str], cells: dict[tuple[str, str], str]) -> None:
    print("| Station | " + " | ".join(trains) + " |")
    print("|---|" + "|".join(["---:"] * len(trains)) + "|")
    for station in stations:
        values = [cells.get((station, train), "") for train in trains]
        print("| " + station + " | " + " | ".join(values) + " |")


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    with source.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    stations, trains, cells = pivot_rows(rows)
    write_markdown_table(stations, trains, cells)


if __name__ == "__main__":
    main()
