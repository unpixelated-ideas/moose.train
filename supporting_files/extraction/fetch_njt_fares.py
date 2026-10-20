#!/usr/bin/env python3
"""Audit current adult fare quotes from NJ Transit's public website, never in-browser."""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

from njt import station_mappings

ENDPOINT = "https://www.njtransit.com/api/graphql/graphql"
SAMPLE_PAIRS = [("NYP", "TRE"), ("TRE", "NYP"), ("NWK", "MET"), ("NYP", "EWR"),
                ("NJT_123", "NYP"), ("NJT_123", "NJT_63"),
                ("NJT_142", "NYP"), ("NJT_142", "NJT_63")]


def amount_cents(value):
    match = re.fullmatch(r"\$(\d+)\.(\d{2})", value or "")
    if not match:
        return None
    cents = int(match[1]) * 100 + int(match[2])
    return cents if cents > 0 else None


def fare_query(pairs, stations, service_date=None):
    fields = []
    for i, (origin, destination) in enumerate(pairs):
        # JSON string literals also provide GraphQL string escaping.
        start = json.dumps(stations[origin]["fare_station_title"])
        end = json.dumps(stations[destination]["fare_station_title"])
        date_argument = f',date:"{service_date:%m/%d/%Y}"' if service_date else ""
        fields.append(f"q{i}:getSchedule(origin:{start},destination:{end}{date_argument})"
                      "{fare{regularFare showMessage}}")
    return "{" + " ".join(fields) + "}"


def parse_quotes(payload, pairs):
    failed = {str(error.get("path", [""])[0]) for error in payload.get("errors", []) if error.get("path")}
    global_error = any(not error.get("path") for error in payload.get("errors", []))
    quotes = []
    for i, (origin, destination) in enumerate(pairs):
        alias = f"q{i}"
        result = (payload.get("data") or {}).get(alias)
        fare = result.get("fare") if isinstance(result, dict) else None
        fare = fare if isinstance(fare, dict) else {}
        cents = amount_cents(fare.get("regularFare"))
        usable = not global_error and alias not in failed and cents is not None and isinstance(fare.get("showMessage"), bool)
        quotes.append({"origin": origin, "destination": destination,
                       "quoted_amount_cents": cents if usable else None,
                       "regular_fare_text": fare.get("regularFare"),
                       "via_secaucus_notice": fare.get("showMessage"),
                       "usable_response": usable,
                       "error_messages": [str(error.get("message", "Unknown GraphQL error"))
                                          for error in payload.get("errors", [])
                                          if not error.get("path") or str(error["path"][0]) == alias]})
    return quotes


def fetch_payload(query):
    request = urllib.request.Request(ENDPOINT, json.dumps({"query": query}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def collect_report(service_date, all_pairs=True):
    stations = {value["station_id"]: value for value in station_mappings().values()}
    pairs = list(itertools.permutations(sorted(stations), 2)) if all_pairs else SAMPLE_PAIRS
    quotes = []
    batches = [pairs[offset:offset + 10] for offset in range(0, len(pairs), 10)]
    def read_batch(batch):
        payload = fetch_payload(fare_query(batch, stations, service_date))
        time.sleep(0.2)
        return parse_quotes(payload, batch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for index, batch_quotes in enumerate(pool.map(read_batch, batches)):
            quotes.extend(batch_quotes)
            if index % 10 == 0 or index + 1 == len(batches):
                print(f"Audited {len(quotes)}/{len(pairs)} directed station pairs", flush=True)
    report = {"source_url": ENDPOINT, "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "effective_date": None, "query_service_date": service_date.isoformat(),
              "source_status": "Undocumented public website interface; quotes require fare-policy validation before publication",
              "quotes": quotes,
              "usable_responses": sum(quote["usable_response"] for quote in quotes),
              "total_pairs": len(pairs), "published": False}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New audit JSON file; existing files are never overwritten")
    parser.add_argument("--all-pairs", action="store_true", help="Audit every directed pair (391 requests for 63 stations)")
    parser.add_argument("--service-date", type=dt.date.fromisoformat,
                        default=dt.datetime.now(ZoneInfo("America/New_York")).date(),
                        help="Planner service date, YYYY-MM-DD (default: today in New York)")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = collect_report(args.service_date, args.all_pairs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(f"{report['usable_responses']}/{report['total_pairs']} responses contain an adult fare; not approved for publication", flush=True)


if __name__ == "__main__":
    main()
