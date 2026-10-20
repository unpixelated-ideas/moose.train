#!/usr/bin/env python3
"""Publish only corroborated NJ Transit adult fares; retain unknowns as unavailable."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import hashlib
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from fetch_njt_fares import ENDPOINT, collect_report
from njt import station_mappings

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "supporting_files/assets/njt_fares.json"
CORE_PAIRS = [("NYP", "TRE"), ("NJT_123", "NJT_63"), ("NJT_142", "NJT_63"),
              ("NJT_123", "NYP"), ("NJT_142", "NYP")]


def compile_snapshot(report, required_pairs=CORE_PAIRS):
    if report.get("source_url") != ENDPOINT or not report.get("query_service_date"):
        raise ValueError("NJ Transit fares require the official source and an explicit service date")
    dt.date.fromisoformat(report["query_service_date"])
    retrieved = dt.datetime.fromisoformat(report["retrieved_at"])
    if retrieved.tzinfo is None:
        raise ValueError("Fare retrieval timestamp must include its time zone")
    stations = {row["station_id"] for row in station_mappings().values()}
    quotes = {}
    for quote in report["quotes"]:
        pair = (quote["origin"], quote["destination"])
        if pair in quotes or not set(pair) <= stations or pair[0] == pair[1]:
            raise ValueError("Duplicate or unknown fare station pair")
        quotes[pair] = quote
    fares = {}
    withheld = []
    for pair, quote in sorted(quotes.items()):
        reverse = quotes.get(tuple(reversed(pair)))
        amount = quote.get("quoted_amount_cents")
        # A disagreement is not resolved by guessing, taking the cheaper price,
        # copying the reverse fare, or adding separate leg prices.
        if (not quote.get("usable_response") or not reverse or not reverse.get("usable_response")
                or type(amount) is not int or amount <= 0
                or reverse.get("quoted_amount_cents") != amount
                or type(quote.get("via_secaucus_notice")) is not bool
                or quote["via_secaucus_notice"] != reverse.get("via_secaucus_notice")):
            withheld.append(">".join(pair))
            continue
        fares[">".join(pair)] = {"amountCents": amount, "viaSecaucusOnly": quote["via_secaucus_notice"]}
    for pair in required_pairs:
        if any(">".join(direction) not in fares for direction in (pair, tuple(reversed(pair)))):
            raise ValueError(f"Missing corroborated core NJ Transit fare: {pair}")
    if not fares:
        raise ValueError("No corroborated NJ Transit fares; preserve the previous site")
    return {"version": 1, "currency": "USD", "sourceUrl": "https://www.njtransit.com/train-to",
            "retrievedAt": report["retrieved_at"], "quoteServiceDate": report["query_service_date"],
            "fares": fares, "withheldPairs": withheld,
            "coverage": {"publishedPairs": len(fares), "queriedPairs": len(quotes)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-report", type=Path, help="Compile an already collected, dated official-source audit")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.from_report:
        report = json.loads(args.from_report.read_text())
    else:
        # Use a complete weekday timetable, including commuter-only stations.
        day = dt.datetime.now(ZoneInfo("America/New_York")).date()
        while day.weekday() >= 5:
            day += dt.timedelta(days=1)
        report = collect_report(day)
    snapshot = compile_snapshot(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(".json.tmp")
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
    temp.replace(args.output)
    if args.output.resolve() == OUTPUT.resolve():
        javascript = "window.MOOSE_NJT_FARES=" + json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + ";\n"
        script_path = OUTPUT.with_suffix(".js")
        script_path.write_text(javascript)
        version = hashlib.sha256(javascript.encode()).hexdigest()[:16]
        page = ROOT / "index.html"
        html, count = re.subn(r'src="supporting_files/assets/njt_fares\.js(?:\?v=[a-f0-9]+)?"',
                             f'src="supporting_files/assets/njt_fares.js?v={version}"', page.read_text())
        if count != 1:
            raise ValueError("Expected one NJ Transit fare script in index.html")
        page.write_text(html)
    print(json.dumps(snapshot["coverage"]))


if __name__ == "__main__":
    main()
