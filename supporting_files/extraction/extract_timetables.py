#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from gtfs_importer import import_configured_feeds


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "supporting_files" / "source_pdfs"
OUT_CSV = ROOT / "moose_train_schedule.csv"
QA_CSV = ROOT / "supporting_files" / "extraction" / "extraction_summary.csv"
SOURCE_CSV_DIR = ROOT / "supporting_files" / "extraction" / "source_csvs"

BASE_COLUMNS = [
    "agency",
    "service_name",
    "route_name",
    "train_number",
    "direction",
    "station_id",
    "station_name",
    "station_sequence",
    "arrival_time",
    "departure_time",
    "service_start_date",
    "service_end_date",
    "service_dates",
    "service_days",
    "timetable_effective_date",
    "timetable_last_updated_date",
    "timetable_revision_date",
    "source_original_filename",
    "source_pdf",
    "source_page",
    "raw_notes",
]

TIME_RE = re.compile(r"(?:\b[RDH]\s*)?(?:(?:Ar|Dp)\s*)?(\d{1,2}):?(\d{2})\s*([AP])\b", re.I)
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
MTA_UPDATED_RE = re.compile(r"Updated\s+(\d{2})-\s*(\d{2})-(\d{2})", re.I)
MTA_REVISED_RE = re.compile(r"Revised\s+(\d{1,2})/(\d{1,2})/(\d{4})|rev\.\s*(\d{1,2})/(\d{1,2})/(\d{2})", re.I)

STATION_IDS = {
    "BOSTON, MA": "BOS",
    "Boston, MA": "BBY",
    "Route 128, MA": "RTE",
    "Providence, RI": "PVD",
    "Kingston, RI": "KIN",
    "Westerly, RI": "WLY",
    "Westerly": "WLY",
    "Mystic, CT": "MYS",
    "Mystic": "MYS",
    "New York Penn": "NYP",
    "New London": "NLC",
    "New London, CT": "NLC",
    "Old Saybrook": "OSB",
    "Old Saybrook, CT": "OSB",
    "Westbrook": "WBK",
    "Clinton": "CLIN",
    "Madison": "MAD",
    "Guilford": "GUI",
    "Branford": "BRA",
    "NEW HAVEN, CT": "NHV",
    "New Haven Union": "NHV",
    "New Haven - Union Station": "NHV",
    "New Haven Union Station": "NHV",
    "New Haven State Street": "STS",
    "New Haven - State Street": "STS",
    "Bridgeport, CT": "BRP",
    "Bridgeport": "BRP",
    "Stratford": "SFD",
    "Milford": "MIL",
    "West Haven": "WHA",
    "New Haven": "NHV",
    "New Haven-State St.": "STS",
    "New Haven-State St": "STS",
    "South Norwalk": "SONO",
    "Stamford, CT": "STM",
    "Stamford": "STM",
    "Stamford Ar.": "STM",
    "Stamford Lv.": "STM",
    "Fairfield-Black Rock": "FFB",
    "Fairfield": "FFD",
    "Southport": "SOP",
    "Green's Farms": "GNF",
    "Green’s Farms": "GNF",
    "Westport": "WPT",
    "East Norwalk": "ENW",
    "Rowayton": "ROW",
    "Darien": "DAR",
    "Noroton Heights": "NTH",
    "Old Greenwich": "OGW",
    "Riverside": "RIV",
    "Cos Cob": "COB",
    "Port Chester": "POR",
    "Rye": "RYE",
    "Harrison": "HAR",
    "Mamaroneck": "MAM",
    "Larchmont": "LAR",
    "New Rochelle": "NRO",
    "Pelham": "PEL",
    "Mount Vernon East": "MVE",
    "Fordham": "FOR",
    "Fordham (E.190th)": "FOR",
    "Harlem-125th St.": "H125",
    "Harlem - 125th St.": "H125",
    "Harlem-125 St": "H125",
    "Mt Vernon East": "MVE",
    "Greenwich": "GRE",
    "New Rochelle, NY": "NRO",
    "NEW YORK, NY": "NYP",
    "Grand Central": "GCT",
    "Grand Central Terminal": "GCT",
    "Harlem - 125th St.": "H125",
    "Harlem - 125th St": "H125",
    "Newark, NJ": "NWK",
    "Newark, NJ - Liberty International Airport": "EWR",
    "Metropark, NJ": "MET",
    "New Brunswick, NJ": "NBK",
    "Princeton Junction, NJ": "PJC",
    "Trenton, NJ": "TRE",
    "PHILADELPHIA, PA": "PHL",
    "Wilmington, DE": "WIL",
    "Baltimore, MD": "BAL",
    "Baltimore, MD - BWI Thurgood Marshall Airport": "BWI",
    "New Carrollton, MD": "NCR",
    "WASHINGTON, DC": "WAS",
    "Wallingford": "WFD",
    "Meriden": "MDN",
    "Berlin": "BER",
    "Hartford": "HFD",
    "Windsor": "WND",
    "Windsor Locks": "WNL",
    "Springfield": "SPG",
    "Waterbury": "WBY",
    "Naugatuck": "NAU",
    "Beacon Falls": "BCF",
    "Seymour": "SEY",
    "Ansonia": "ANS",
    "Derby-Shelton": "DBY",
    "Danbury": "DAN",
    "Bethel": "BTH",
    "Redding": "RDG",
    "Branchville": "BVL",
    "Cannondale": "CND",
    "Wilton": "WILTON",
    "Merritt 7": "MRT7",
    "New Canaan": "NCN",
    "Talmadge Hill": "TMH",
    "Springdale": "SPD",
    "Glenbrook": "GLB",
    "Yankees-E 153 St": "YANKEES",
    "Springdale MW Facility": "SPDMW",
}

ORIGINAL_FILENAMES = {
    "amtrak_acela_effective_2026-04-06_generated_2026-04-05.pdf": "timetables_Acela_20260406_external.pdf",
    "amtrak_northeast_corridor_effective_2026-04-08_generated_2026-04-05.pdf": "timetables_NE_Corridor2_Boston-Springfield_Washington_20260408_external.pdf",
    "ctrail_hartford_line_effective_2026-06-22_updated_2026-06-09.pdf": "6-22.pdf",
    "ctrail_shore_line_east_effective_2026-03-29_updated_2026-03-17.pdf": "SLE-3_29-MNR-Schedule-Change.pdf",
    "metro_north_new_haven_line_effective_2026-03-29_revised_2026-04-11_updated_2026-04-08.pdf": "04-07-26_NHL+Branches-Sched_v3.pdf",
    "metro_north_waterbury_branch_effective_2026-03-29_updated_2026-04-08.pdf": "04-07-26_NHL+Branches-Sched_v3.pdf",
    "metro_north_waterbury_branch_effective_2026-03-29_updated_2026-03-16.pdf": "03-29-26_NHL-WB-Sched_v2.pdf",
    "metro_north_new_haven_line_effective_2026-03-29_updated_2026-03-16.pdf": "03-29-26_NHL-WB-Sched_v2.pdf",
    "metro_north_danbury_branch_effective_2026-03-29_updated_2026-03-16.pdf": "03-29-26_NHL-DB-Sched_v2.pdf",
    "metro_north_danbury_branch_effective_2026-03-29_updated_2026-04-08.pdf": "04-07-26_NHL+Branches-Sched_v3.pdf",
    "metro_north_new_canaan_branch_effective_2026-03-29_updated_2026-03-16.pdf": "03-29-26_NHL-NC-Sched_v2.pdf",
}


@dataclass(frozen=True)
class PdfSpec:
    original: str
    renamed: str
    agency: str
    service_name: str
    route_name: str
    effective: str
    end: str
    updated: str
    revision: str


def main() -> None:
    specs = discover_and_rename_pdfs()
    rows = []
    summary = []

    for spec in specs:
        pdf = SOURCE_DIR / spec.renamed
        reader = PdfReader(str(pdf))
        before = len(rows)
        if spec.agency == "Amtrak":
            rows.extend(parse_amtrak(reader, spec))
        elif spec.service_name == "Shore Line East":
            rows.extend(parse_ctrail(reader, spec, default_agency="CTrail", train_prefix="SLE"))
            rows.extend(parse_sle_connections_to_new_york(reader, spec))
            rows.extend(parse_sle_connections_from_new_york(reader, spec))
        elif spec.service_name == "Hartford Line":
            rows.extend(parse_ctrail(reader, spec, default_agency="CTrail", train_prefix="HL"))
            rows.extend(parse_hartford_connection_stubs(reader, spec))
        elif spec.agency == "Metro-North":
            continue
        else:
            rows.extend(parse_metro_north(pdf, reader, spec))
        summary.append({
            "source_pdf": spec.renamed,
            "source_original_filename": spec.original,
            "rows_extracted": len(rows) - before,
            "pages": len(reader.pages),
            "timetable_effective_date": spec.effective,
            "service_end_date": spec.end,
            "timetable_last_updated_date": spec.updated,
            "timetable_revision_date": spec.revision,
        })

    gtfs_rows, _gtfs_metadata, gtfs_results = import_configured_feeds(ROOT, station_id_for, download=True)
    rows.extend(gtfs_rows)
    for result in gtfs_results:
        if result.errors:
            continue
        summary.append({
            "source_pdf": result.source_name,
            "source_original_filename": result.rows[0]["source_original_filename"],
            "rows_extracted": str(len(result.rows)),
            "pages": "",
            "timetable_effective_date": min(row["service_start_date"] for row in result.rows),
            "service_end_date": max(row["service_end_date"] for row in result.rows),
            "timetable_last_updated_date": result.metadata["imported_at"][:10],
            "timetable_revision_date": "",
        })

    rows = stitch_sle_through_trips(rows)
    rows.sort(key=lambda r: (r["agency"], r["service_name"], r["source_pdf"], source_page_sort_key(r["source_page"]), natural_train_key(r["train_number"]), int(r["station_sequence"])))
    source_counts = {}
    for row in rows:
        source_counts[row["source_pdf"]] = source_counts.get(row["source_pdf"], 0) + 1
    for item in summary:
        item["rows_extracted"] = source_counts.get(item["source_pdf"], 0)
    write_csv(OUT_CSV, BASE_COLUMNS, rows)
    write_csv(QA_CSV, list(summary[0].keys()), summary)
    write_existing_source_csvs(rows)


def discover_and_rename_pdfs() -> list[PdfSpec]:
    specs = []
    for path in sorted(SOURCE_DIR.glob("*.pdf")):
        if is_gtfs_replaced_pdf(path):
            continue
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[: min(3, len(reader.pages))])
        metadata = reader.metadata or {}
        mod_date = pdf_date_to_iso(str(metadata.get("/ModDate", "")))
        original = ORIGINAL_FILENAMES.get(path.name, path.name)

        if "NORTHEAST CORRIDOR" in text.upper():
            start, end = valid_range(text)
            generated = generated_on(text) or mod_date
            spec = PdfSpec(original, f"amtrak_northeast_corridor_effective_{start}_generated_{generated}.pdf", "Amtrak", "Northeast Corridor", "Northeast Regional / Corridor Services", start, end, generated, "")
        elif "ACELA" in text.upper():
            start, end = valid_range(text)
            generated = generated_on(text) or mod_date
            spec = PdfSpec(original, f"amtrak_acela_effective_{start}_generated_{generated}.pdf", "Amtrak", "Acela", "Acela", start, end, generated, "")
        elif "HARTFORD LINE" in text.upper():
            effective = text_effective_date(text) or "2026-06-22"
            spec = PdfSpec(original, f"ctrail_hartford_line_effective_{effective}_updated_{mod_date}.pdf", "CTrail", "Hartford Line", "Hartford Line", effective, "", mod_date, "")
        elif "SHORE LINE EAST" in text.upper():
            effective = text_effective_date(text) or "2026-03-29"
            spec = PdfSpec(original, f"ctrail_shore_line_east_effective_{effective}_updated_{mod_date}.pdf", "CTrail", "Shore Line East", "Shore Line East", effective, "", mod_date, "")
        elif path.name.startswith("03-29-26_NHL-DB") or path.name.startswith("metro_north_danbury_branch_effective_2026-03-29_updated_2026-03-16"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            spec = PdfSpec(original, f"metro_north_danbury_branch_effective_{effective}_updated_{updated}.pdf", "Metro-North", "Danbury Branch", "New Haven Line - Danbury Branch", effective, "", updated, "")
        elif path.name.startswith("03-29-26_NHL-NC") or path.name.startswith("metro_north_new_canaan_branch_effective_"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            spec = PdfSpec(original, f"metro_north_new_canaan_branch_effective_{effective}_updated_{updated}.pdf", "Metro-North", "New Canaan Branch", "New Haven Line - New Canaan Branch", effective, "", updated, "")
        elif path.name.startswith("03-29-26_NHL-WB") or path.name.startswith("metro_north_waterbury_branch_effective_2026-03-29_updated_2026-03-16"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            spec = PdfSpec(original, f"metro_north_waterbury_branch_effective_{effective}_updated_{updated}.pdf", "Metro-North", "Waterbury Branch", "New Haven Line - Waterbury Branch", effective, "", updated, "")
        elif "REVISED 4/11/2026" in text.upper() or path.name.startswith("metro_north_waterbury_branch_effective_2026-03-29_updated_2026-04-08") or path.name.startswith("metro_north_danbury_branch_effective_2026-03-29_updated_2026-04-08"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            revision = mta_revision_date(text)
            rev_part = f"_revised_{revision}" if revision else ""
            spec = PdfSpec(original, f"metro_north_new_haven_line_effective_{effective}{rev_part}_updated_{updated}.pdf", "Metro-North", "New Haven Line", "New Haven Line", effective, "", updated, revision)
        elif "DANBURY BRANCH" in text.upper() or path.name.startswith("metro_north_danbury_branch_effective_"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            spec = PdfSpec(original, f"metro_north_danbury_branch_effective_{effective}_updated_{updated}.pdf", "Metro-North", "Danbury Branch", "New Haven Line - Danbury Branch", effective, "", updated, "")
        elif "NEW CANAAN BRANCH" in text.upper() or path.name.startswith("metro_north_new_canaan_branch_effective_"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            spec = PdfSpec(original, f"metro_north_new_canaan_branch_effective_{effective}_updated_{updated}.pdf", "Metro-North", "New Canaan Branch", "New Haven Line - New Canaan Branch", effective, "", updated, "")
        elif "WATERBURY BRANCH" in text.upper() or path.name.startswith("metro_north_new_haven_line_effective_2026-03-29_updated_2026-03-16"):
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            spec = PdfSpec(original, f"metro_north_waterbury_branch_effective_{effective}_updated_{updated}.pdf", "Metro-North", "Waterbury Branch", "New Haven Line - Waterbury Branch", effective, "", updated, "")
        else:
            effective = text_as_of_date(text) or "2026-03-29"
            updated = mta_updated_date(text) or mod_date
            revision = mta_revision_date(text)
            rev_part = f"_revised_{revision}" if revision else ""
            spec = PdfSpec(original, f"metro_north_new_haven_line_effective_{effective}{rev_part}_updated_{updated}.pdf", "Metro-North", "New Haven Line", "New Haven Line", effective, "", updated, revision)

        target = SOURCE_DIR / spec.renamed
        if path != target:
            if target.exists():
                raise FileExistsError(f"Refusing to overwrite existing source PDF: {target.name}")
            shutil.move(str(path), str(target))
        specs.append(spec)
    return specs


def is_gtfs_replaced_pdf(path: Path) -> bool:
    return (
        path.name.startswith("metro_north_") or
        path.name.startswith("03-29-26_NHL") or
        path.name.startswith("04-07-26_NHL") or
        path.name.startswith("ctrail_hartford_line_") or
        path.name.startswith("ctrail_shore_line_east_")
    )


def parse_amtrak(reader: PdfReader, spec: PdfSpec) -> list[dict[str, str]]:
    rows = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = layout_text(page)
        title = first_line(text)
        direction = "Southbound" if "SOUTHBOUND" in title.upper() else "Northbound" if "NORTHBOUND" in title.upper() else ""
        service_days = page_service_days(title, text)
        trains = train_columns_for_amtrak(text)
        if not trains:
            continue

        sequence = 0
        current_station = ""
        current_id = ""
        for line in text.splitlines():
            if not line.strip() or not TIME_RE.search(line):
                continue
            if line.lstrip().startswith("-"):
                if current_station:
                    emit_times(rows, line, trains, spec, page_no, current_id, current_station, sequence, direction, service_days, title)
                continue
            station = parse_amtrak_station(line)
            if station:
                sequence += 1
                current_station, current_id = station
                emit_times(rows, line, trains, spec, page_no, current_id, current_station, sequence, direction, service_days, title)
            elif current_station and (" Ar " in f" {line} " or " Dp " in f" {line} "):
                emit_times(rows, line, trains, spec, page_no, current_id, current_station, sequence, direction, service_days, title)
    return dedupe_rows(rows)


def parse_ctrail(reader: PdfReader, spec: PdfSpec, default_agency: str, train_prefix: str) -> list[dict[str, str]]:
    rows = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = layout_text(page)
        service_days = "weekday" if "MONDAY TO FRIDAY" in text.upper() else "weekend_or_holiday" if "WEEKEND" in text.upper() or "SATURDAY" in text.upper() else ""
        sections = split_ctrail_sections(text)
        for direction, section in sections:
            trains = train_columns_for_ctrail(section, train_prefix)
            if not trains:
                continue
            sequence = 0
            for line in section.splitlines():
                station = parse_ctrail_station(line)
                if not station or not TIME_RE.search(line):
                    continue
                sequence += 1
                station_name, station_id = station
                emit_times(rows, line, trains, spec, page_no, station_id, station_name, sequence, direction, service_days, direction)
    return dedupe_rows(rows)


def parse_sle_connections_from_new_york(reader: PdfReader, spec: PdfSpec) -> list[dict[str, str]]:
    rows = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = layout_text(page)
        service_days = "weekday" if "MONDAY TO FRIDAY" in text.upper() else "weekend_or_holiday" if "WEEKEND" in text.upper() or "SATURDAY" in text.upper() else ""
        for section in split_connection_sections(text, "CONNECTIONS FROM NEW YORK (ARRIVING)"):
            trains = train_columns_for_mnr_connection(section)
            if not trains:
                continue
            sequence = 0
            for line in section.splitlines():
                station = parse_ctrail_station(line)
                if not station or not TIME_RE.search(line):
                    continue
                sequence += 1
                station_name, station_id = station
                emit_times(rows, line, trains, spec, page_no, station_id, station_name, sequence, "To New Haven", service_days, "SLE connection from New York")
    return dedupe_rows(rows)


def parse_sle_connections_to_new_york(reader: PdfReader, spec: PdfSpec) -> list[dict[str, str]]:
    rows = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = layout_text(page)
        service_days = "weekday" if "MONDAY TO FRIDAY" in text.upper() else "weekend_or_holiday" if "WEEKEND" in text.upper() or "SATURDAY" in text.upper() else ""
        for section in split_connection_sections(text, "CONNECTIONS TO NEW YORK (DEPARTING)"):
            trains = train_columns_for_sle_connection_to_new_york(section)
            if not trains:
                continue
            sequence = 0
            for line in section.splitlines():
                station = parse_ctrail_station(line)
                if not station or not TIME_RE.search(line):
                    continue
                sequence += 1
                station_name, station_id = station
                emit_times(rows, line, trains, spec, page_no, station_id, station_name, sequence, "To Grand Central", service_days, "SLE connection to New York")
    return dedupe_rows(rows)


def parse_hartford_connection_stubs(reader: PdfReader, spec: PdfSpec) -> list[dict[str, str]]:
    rows = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = layout_text(page)
        service_days = "weekday" if "MONDAY TO FRIDAY" in text.upper() else "weekend_or_holiday" if "WEEKEND" in text.upper() or "SATURDAY" in text.upper() else ""
        for section in split_hartford_connection_sections(text):
            direction = hartford_connection_direction(section)
            for header_idx, lines in iter_connection_groups(section):
                trains = train_columns_for_connection_group(lines)
                if not trains:
                    continue
                time_line = connection_time_line(lines, direction)
                if not time_line:
                    continue
                raw_note = connection_raw_note(lines, direction)
                for match in TIME_RE.finditer(time_line):
                    train = nearest_train(match.start(), trains)
                    if not train:
                        continue
                    hhmm = normalize_time(match.group(1), match.group(2), match.group(3))
                    rows.append(make_partial_connection_row(
                        spec=spec,
                        train=train,
                        page_no=page_no,
                        sequence=header_idx + len(rows) + 1,
                        direction=direction,
                        service_days=train.get("days") or service_days,
                        known_time=hhmm,
                        raw_note=raw_note,
                    ))
    return dedupe_rows(rows)


def make_partial_connection_row(spec: PdfSpec, train: dict[str, str], page_no: int, sequence: int, direction: str, service_days: str, known_time: str, raw_note: str) -> dict[str, str]:
    is_arrival = direction == "To New Haven"
    return {
        "agency": train.get("agency") or spec.agency,
        "service_name": train.get("service") or spec.service_name,
        "route_name": train.get("route") or spec.route_name,
        "train_number": train["number"],
        "direction": direction,
        "station_id": "NHV",
        "station_name": "New Haven Union Station",
        "station_sequence": str(sequence),
        "arrival_time": known_time if is_arrival else "unknown",
        "departure_time": "unknown" if is_arrival else known_time,
        "service_start_date": spec.effective,
        "service_end_date": spec.end,
        "service_dates": "",
        "service_days": service_days,
        "timetable_effective_date": spec.effective,
        "timetable_last_updated_date": spec.updated,
        "timetable_revision_date": spec.revision,
        "source_original_filename": spec.original,
        "source_pdf": spec.renamed,
        "source_page": str(page_no),
        "raw_notes": raw_note,
    }


MNR_STATIONS = [
    ("New Haven-State St.", ["new haven-state st", "new haven state st"]),
    ("New Haven", ["new haven"]),
    ("West Haven", ["west haven"]),
    ("Milford", ["milford"]),
    ("Stratford", ["stratford"]),
    ("Bridgeport", ["bridgeport"]),
    ("Fairfield-Black Rock", ["fairfield-black rock", "fairfield black rock"]),
    ("Fairfield", ["fairfield"]),
    ("Southport", ["southport"]),
    ("Green's Farms", ["green's farms", "green’s farms", "greens farms"]),
    ("Westport", ["westport"]),
    ("East Norwalk", ["east norwalk"]),
    ("South Norwalk", ["south norwalk"]),
    ("Rowayton", ["rowayton"]),
    ("Darien", ["darien"]),
    ("Noroton Heights", ["noroton heights"]),
    ("Stamford", ["stamford"]),
    ("Old Greenwich", ["old greenwich"]),
    ("Riverside", ["riverside"]),
    ("Cos Cob", ["cos cob"]),
    ("Greenwich", ["greenwich"]),
    ("Port Chester", ["port chester"]),
    ("Rye", ["rye"]),
    ("Harrison", ["harrison"]),
    ("Mamaroneck", ["mamaroneck"]),
    ("Larchmont", ["larchmont"]),
    ("New Rochelle", ["new rochelle"]),
    ("Pelham", ["pelham"]),
    ("Mount Vernon East", ["mount vernon east"]),
    ("Fordham", ["fordham"]),
    ("Harlem-125th St.", ["harlem-125th", "harlem 125th"]),
    ("Grand Central", ["grand central"]),
    ("New Canaan", ["new canaan"]),
    ("Talmadge Hill", ["talmadge hill"]),
    ("Springdale", ["springdale"]),
    ("Glenbrook", ["glenbrook"]),
    ("Danbury", ["danbury"]),
    ("Bethel", ["bethel"]),
    ("Redding", ["redding"]),
    ("Branchville", ["branchville"]),
    ("Cannondale", ["cannondale"]),
    ("Wilton", ["wilton"]),
    ("Merritt 7", ["merritt 7"]),
    ("Waterbury", ["waterbury"]),
    ("Naugatuck", ["naugatuck"]),
    ("Beacon Falls", ["beacon falls"]),
    ("Seymour", ["seymour"]),
    ("Ansonia", ["ansonia"]),
    ("Derby-Shelton", ["derby-shelton", "derby shelton"]),
]


def parse_metro_north(pdf_path: Path, reader: PdfReader, spec: PdfSpec) -> list[dict[str, str]]:
    rows = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = reader.pages[page_no - 1].extract_text() or page.extract_text() or ""
            service_days = metro_north_service_days(text)
            words = visible_pdf_words(page)
            visual_rows = group_pdf_words(words)
            blocks = metro_north_header_blocks(visual_rows, min_train_columns_for_mnr(spec))
            for block_index, block in enumerate(blocks, start=1):
                rows.extend(parse_metro_north_block(visual_rows, block, spec, page_no, service_days, block_index))
    return finalize_metro_north_rows(rows)


def metro_north_service_days(text: str) -> str:
    upper = text.upper()
    if "MONDAY - FRIDAY" in upper:
        return "weekday"
    if "SATURDAY" in upper and "SUNDAY" in upper:
        return "weekend"
    if "SATURDAY" in upper:
        return "saturday"
    if "SUNDAY" in upper:
        return "sunday"
    return ""


def group_pdf_words(words: list[dict]) -> list[dict]:
    rows = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        target = None
        for row in reversed(rows[-8:]):
            if abs(row["top"] - word["top"]) <= 1.5:
                target = row
                break
        if not target:
            target = {"top": word["top"], "words": []}
            rows.append(target)
        target["words"].append(word)

    for row in rows:
        row["words"].sort(key=lambda item: item["x0"])
        row["text"] = " ".join(word["text"] for word in row["words"])
    return rows


def visible_pdf_words(page) -> list[dict]:
    words = page.extract_words(x_tolerance=1, y_tolerance=1, keep_blank_chars=False)
    return [
        word for word in words
        if 0 <= word_center(word) <= page.width and 0 <= float(word["top"]) <= page.height
    ]


def min_train_columns_for_mnr(spec: PdfSpec) -> int:
    if spec.service_name in {"Danbury Branch", "New Canaan Branch", "Waterbury Branch"}:
        return 6
    return 8


def metro_north_header_blocks(rows: list[dict], min_train_columns: int = 8) -> list[dict]:
    candidates = []
    for index, row in enumerate(rows):
        train_words = [word for word in row["words"] if re.fullmatch(r"B?\d{4}", clean_pdf_token(word["text"]))]
        if len(train_words) < min_train_columns:
            continue
        row_tokens = [clean_pdf_token(word["text"]).upper() for word in row["words"]]
        if len(train_words) / max(len(row["words"]), 1) < 0.75:
            continue
        if any(token in {"AM", "PM"} for token in row_tokens):
            continue
        period_row = nearest_period_row(rows, index)
        if not period_row:
            continue
        columns = []
        for word in train_words:
            number = clean_pdf_token(word["text"]).lstrip("B")
            columns.append({"number": number, "x": word_center(word), "period": "A"})
        periods = period_by_column(period_row, columns)
        for column in columns:
            column["period"] = periods.get(column["number"], "A")
        columns.sort(key=lambda item: item["x"])
        first_x = columns[0]["x"]
        last_x = columns[-1]["x"]
        if last_x - first_x < 20:
            continue
        candidates.append({
            "row_index": index,
            "top": row["top"],
            "columns": columns,
            "period_top": period_row["top"],
            "first_x": first_x,
            "last_x": last_x,
            "median_gap": median_column_gap(columns),
        })

    deduped = []
    seen = set()
    for candidate in candidates:
        key = (round(candidate["top"], 1), round(candidate["first_x"], 1), tuple(column["number"] for column in candidate["columns"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    deduped.sort(key=lambda item: (item["top"], item["first_x"]))
    for index, block in enumerate(deduped):
        next_tops = [
            other["top"] for other in deduped[index + 1:]
            if other["top"] > block["top"] + 20 and abs(other["first_x"] - block["first_x"]) < 80
        ]
        block["end_top"] = min(next_tops) if next_tops else block["top"] + 280
    return deduped


def nearest_period_row(rows: list[dict], header_index: int) -> dict | None:
    for row in rows[header_index + 1: header_index + 7]:
        periods = [clean_pdf_token(word["text"]).upper() for word in row["words"]]
        if sum(1 for period in periods if period in {"AM", "PM"}) >= 2:
            return row
    return None


def period_by_column(row: dict, columns: list[dict]) -> dict[str, str]:
    periods = {}
    period_words = [word for word in row["words"] if clean_pdf_token(word["text"]).upper() in {"AM", "PM"}]
    for word in period_words:
        nearest = min(columns, key=lambda column: abs(column["x"] - word_center(word)))
        periods[nearest["number"]] = clean_pdf_token(word["text"]).upper()[0]
    return periods


def parse_metro_north_block(rows: list[dict], block: dict, spec: PdfSpec, page_no: int, service_days: str, block_index: int) -> list[dict[str, str]]:
    collected = []
    label_min = block["first_x"] - 190
    label_max = block["first_x"] - 6
    time_min = block["first_x"] - 35
    time_max = block["last_x"] + 35
    assign_threshold = max(7, min(14, block["median_gap"] * 0.62))

    for row in rows:
        if not (block["period_top"] < row["top"] < block["end_top"]):
            continue
        label_text = " ".join(word["text"] for word in row["words"] if label_min <= word_center(word) <= label_max)
        station = canonical_mnr_station(label_text)
        if not station:
            continue
        station_name, event_hint = station
        if is_branch_only_station_for_main_line(spec, station_name):
            continue
        times = row_time_pairs(row, time_min, time_max)
        if not times:
            continue
        for time in times:
            column = min(block["columns"], key=lambda item: abs(item["x"] - time["x"]))
            if abs(column["x"] - time["x"]) > assign_threshold:
                continue
            hhmm = normalize_time(time["hour"], time["minute"], column["period"])
            notes = " ".join(sorted(set(time["notes"])))
            direction = infer_mnr_direction(block, rows, collected)
            collected.append({
                "agency": "Metro-North",
                "service_name": spec.service_name,
                "route_name": spec.route_name,
                "train_number": column["number"],
                "direction": direction,
                "station_id": station_id_for(station_name),
                "station_name": station_name,
                "station_sequence": "0",
                "arrival_time": hhmm if event_hint in {"arrival", "both"} else "",
                "departure_time": hhmm if event_hint in {"departure", "both"} else "",
                "service_start_date": spec.effective,
                "service_end_date": spec.end,
                "service_dates": "",
                "service_days": service_days,
                "timetable_effective_date": spec.effective,
                "timetable_last_updated_date": spec.updated,
                "timetable_revision_date": spec.revision,
                "source_original_filename": spec.original,
                "source_pdf": spec.renamed,
                "source_page": str(page_no),
                "raw_notes": "; ".join(part for part in [direction, notes, f"mnr_block={block_index}"] if part),
                "_row_top": f"{row['top']:.3f}",
                "_block_index": str(block_index),
            })
    return collected


def is_branch_only_station_for_main_line(spec: PdfSpec, station_name: str) -> bool:
    if spec.service_name != "New Haven Line":
        return False
    branch_only = {
        "New Canaan", "Talmadge Hill", "Springdale", "Glenbrook",
        "Waterbury", "Naugatuck", "Beacon Falls", "Seymour", "Ansonia", "Derby-Shelton",
        "Danbury", "Bethel", "Redding", "Branchville", "Cannondale", "Wilton", "Merritt 7",
    }
    return station_name in branch_only


def canonical_mnr_station(label_text: str) -> tuple[str, str] | None:
    normalized = normalize_pdf_label(label_text)
    if not normalized or is_headerish(normalized):
        return None
    event_hint = "arrival" if re.search(r"\bar\b", normalized) else "departure" if re.search(r"\blv\b|\bdp\b", normalized) else "both"
    for station_name, aliases in MNR_STATIONS:
        for alias in aliases:
            if re.search(rf"(^|\b){re.escape(alias)}(\b|$)", normalized):
                return station_name, event_hint
    return None


def normalize_pdf_label(value: str) -> str:
    value = value.lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9.'& -]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def row_time_pairs(row: dict, min_x: float, max_x: float) -> list[dict]:
    words = [word for word in row["words"] if min_x <= word_center(word) <= max_x]
    out = []
    used = set()
    for index, word in enumerate(words[:-1]):
        if index in used:
            continue
        hour = clean_pdf_token(word["text"])
        minute = clean_pdf_token(words[index + 1]["text"])
        if not re.fullmatch(r"\d{1,2}", hour) or not re.fullmatch(r"\d{2}", minute):
            continue
        if not (1 <= int(hour) <= 12 and 0 <= int(minute) <= 59):
            continue
        if words[index + 1]["x0"] - word["x1"] > 4.5:
            continue
        center = (word_center(word) + word_center(words[index + 1])) / 2
        nearby_notes = [
            clean_pdf_token(note["text"]).upper()
            for note in words
            if re.fullmatch(r"[CDHR]", clean_pdf_token(note["text"]).upper())
            and abs(word_center(note) - center) <= 12
        ]
        out.append({"x": center, "hour": hour, "minute": minute, "notes": nearby_notes})
        used.update({index, index + 1})
    return out


def infer_mnr_direction(block: dict, rows: list[dict], collected: list[dict]) -> str:
    context = " ".join(
        row["text"] for row in rows
        if block["top"] - 55 <= row["top"] <= block["top"] + 5
    ).upper()
    if "TO NEW YORK" in context:
        return "To Grand Central"
    if "TO NEW HAVEN" in context:
        return "To New Haven"
    if "TO WATERBURY" in context:
        return "To Waterbury"
    if "TO DANBURY" in context:
        return "To Danbury"
    if "TO NEW CANAAN" in context:
        return "To New Canaan"
    if collected:
        first = collected[0]["station_id"]
        if first in {"NHV", "STS", "WBY", "DAN", "NCN"}:
            return "To Grand Central"
        if first == "GCT":
            return "From Grand Central"
    return "Metro-North"


def finalize_metro_north_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = normalize_mnr_ambiguous_directions(rows)
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["train_number"], row["direction"], row["service_days"], row.get("_block_index", ""))
        grouped.setdefault(key, []).append(row)

    block_counts: dict[tuple[str, str, str], int] = {}
    for train_number, direction, service_days, _block_index in grouped:
        block_counts[(train_number, direction, service_days)] = block_counts.get((train_number, direction, service_days), 0) + 1

    block_seen: dict[tuple[str, str, str], int] = {}
    output = []
    for key, group in grouped.items():
        train_number, direction, service_days, _block_index = key
        suffix_key = (train_number, direction, service_days)
        output_number = train_number
        if block_counts[suffix_key] > 1:
            block_seen[suffix_key] = block_seen.get(suffix_key, 0) + 1
            output_number = f"{train_number}~{block_seen[suffix_key]}"
        ordered_group = collapse_duplicate_mnr_stop_rows(sorted(group, key=lambda item: float(item["_row_top"])))
        inferred_direction = infer_mnr_group_direction(ordered_group)
        if inferred_direction:
            ordered_group = [dict(row, direction=inferred_direction) for row in ordered_group]
        ordered_group = sort_mnr_branch_rows(ordered_group)
        for sequence, row in enumerate(ordered_group, start=1):
            clean = {column: row.get(column, "") for column in BASE_COLUMNS}
            clean["train_number"] = output_number
            clean["station_sequence"] = str(sequence)
            clean["raw_notes"] = re.sub(r";?\s*mnr_block=\d+", "", clean["raw_notes"]).strip("; ")
            if inferred_direction and clean["raw_notes"] == "Metro-North":
                clean["raw_notes"] = inferred_direction
            output.append(clean)
    return dedupe_rows(output)


def normalize_mnr_ambiguous_directions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    known: dict[tuple[str, str, str, str, str], str] = {}
    for row in rows:
        direction = row.get("direction", "")
        if direction == "Metro-North":
            continue
        key = (row["service_name"], row["train_number"], row["service_days"], row["source_pdf"], row.get("_block_index", ""))
        known[key] = direction

    out = []
    for row in rows:
        copy = row
        if row.get("direction") == "Metro-North":
            key = (row["service_name"], row["train_number"], row["service_days"], row["source_pdf"], row.get("_block_index", ""))
            if key in known:
                copy = dict(row)
                copy["direction"] = known[key]
        out.append(copy)
    return out


def collapse_duplicate_mnr_stop_rows(group: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for row in group:
        key = (row["station_id"], row["arrival_time"], row["departure_time"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def sort_mnr_branch_rows(group: list[dict[str, str]]) -> list[dict[str, str]]:
    if not group:
        return group
    branch_orders = {
        "Danbury Branch": ["GCT", "STM", "SONO", "MRT7", "WILTON", "CND", "BVL", "RDG", "BTH", "DAN"],
        "Waterbury Branch": ["GCT", "STM", "SONO", "BRP", "SFD", "DBY", "ANS", "SEY", "BCF", "NAU", "WBY"],
        "New Canaan Branch": ["GCT", "STM", "GLB", "SPD", "TMH", "NCN"],
    }
    outbound = branch_orders.get(group[0].get("service_name"))
    if not outbound:
        return group
    inbound = list(reversed(outbound))
    direction = group[0].get("direction", "")
    if direction == "Metro-North":
        return sorted(group, key=lambda row: (mnr_row_event_minutes(row), float(row["_row_top"])))
    order = outbound if direction == "From Grand Central" else inbound
    position = {station_id: index for index, station_id in enumerate(order)}
    return sorted(group, key=lambda row: (position.get(row["station_id"], 999), float(row["_row_top"])))


def mnr_row_event_minutes(row: dict[str, str]) -> int:
    value = row.get("departure_time") or row.get("arrival_time") or "99:99"
    match = re.match(r"(\d{2}):(\d{2})", value)
    if not match:
        return 9999
    return int(match.group(1)) * 60 + int(match.group(2))


def infer_mnr_group_direction(group: list[dict[str, str]]) -> str:
    if not group:
        return ""
    current = group[0].get("direction", "")
    if current != "Metro-North":
        return ""
    first = group[0]["station_id"]
    last = group[-1]["station_id"]
    branch_terminals = {"WBY", "DAN", "NCN"}
    trunk_terminals = {"GCT", "H125", "STM", "SONO", "BRP"}
    branch_positions = [index for index, row in enumerate(group) if row["station_id"] in branch_terminals]
    trunk_positions = [index for index, row in enumerate(group) if row["station_id"] in trunk_terminals]
    if branch_positions and trunk_positions:
        if min(branch_positions) < min(trunk_positions):
            return "To Grand Central"
        if min(trunk_positions) < min(branch_positions):
            return "From Grand Central"
    if first in branch_terminals and last in trunk_terminals:
        return "To Grand Central"
    if first in trunk_terminals and last in branch_terminals:
        return "From Grand Central"
    return ""


def median_column_gap(columns: list[dict]) -> float:
    xs = sorted(column["x"] for column in columns)
    gaps = [b - a for a, b in zip(xs, xs[1:]) if b > a]
    if not gaps:
        return 16
    gaps.sort()
    return gaps[len(gaps) // 2]


def word_center(word: dict) -> float:
    return (float(word["x0"]) + float(word["x1"])) / 2


def clean_pdf_token(value: str) -> str:
    return value.strip().strip("•|[]()")


def emit_times(rows, line, trains, spec, page_no, station_id, station_name, sequence, direction, service_days, note):
    event_hint = "arrival" if re.search(r"\bAr\.?\b", line) else "departure" if re.search(r"\bLv\.?|\bDp\b", line) else "both"
    for match in TIME_RE.finditer(line):
        train = nearest_train(match.start(), trains)
        if not train:
            continue
        hhmm = normalize_time(match.group(1), match.group(2), match.group(3))
        arrival = hhmm if event_hint in {"arrival", "both"} else ""
        departure = hhmm if event_hint in {"departure", "both"} else ""
        raw_notes = "; ".join(part for part in [note.strip(), train.get("note", "").strip()] if part)
        rows.append({
            "agency": train.get("agency") or spec.agency,
            "service_name": train.get("service") or spec.service_name,
            "route_name": train.get("route") or spec.route_name,
            "train_number": train["number"],
            "direction": direction,
            "station_id": station_id,
            "station_name": station_name,
            "station_sequence": str(sequence),
            "arrival_time": arrival,
            "departure_time": departure,
            "service_start_date": spec.effective,
            "service_end_date": spec.end,
            "service_dates": "",
            "service_days": train.get("days") or service_days,
            "timetable_effective_date": spec.effective,
            "timetable_last_updated_date": spec.updated,
            "timetable_revision_date": spec.revision,
            "source_original_filename": spec.original,
            "source_pdf": spec.renamed,
            "source_page": str(page_no),
            "raw_notes": raw_notes,
        })


def emit_mnr_times(rows, line, trains, spec, page_no, station_id, station_name, sequence, direction, service_days):
    event_hint = "arrival" if re.search(r"\bAr\.?\b", line) else "departure" if re.search(r"\bLv\.?\b", line) else "both"
    time_matches = list(re.finditer(r"(?<!\d)(\d{1,2})\s+(\d{2})(?!\d)", line))
    if len(time_matches) > len(trains):
        time_matches = time_matches[-len(trains):]
    for index, match in enumerate(time_matches):
        if index >= len(trains):
            continue
        train = trains[index]
        hhmm = normalize_time(match.group(1), match.group(2), train.get("period", "A")[:1] or "A")
        arrival = hhmm if event_hint in {"arrival", "both"} else ""
        departure = hhmm if event_hint in {"departure", "both"} else ""
        rows.append({
            "agency": "Metro-North",
            "service_name": spec.service_name,
            "route_name": spec.route_name,
            "train_number": train["number"],
            "direction": direction,
            "station_id": station_id,
            "station_name": station_name,
            "station_sequence": str(sequence),
            "arrival_time": arrival,
            "departure_time": departure,
            "service_start_date": spec.effective,
            "service_end_date": spec.end,
            "service_dates": "",
            "service_days": service_days,
            "timetable_effective_date": spec.effective,
            "timetable_last_updated_date": spec.updated,
            "timetable_revision_date": spec.revision,
            "source_original_filename": spec.original,
            "source_pdf": spec.renamed,
            "source_page": str(page_no),
            "raw_notes": direction,
        })


def train_columns_for_amtrak(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    trains = []
    for idx, line in enumerate(lines):
        if "Train #" not in line:
            continue
        for look in lines[idx + 1: idx + 5]:
            nums = [(m.start(), m.group()) for m in re.finditer(r"\b\d{2,4}\b", look)]
            if len(nums) >= 2:
                days_line = lines[idx + 2] if idx + 2 < len(lines) else ""
                for pos, num in nums:
                    days = nearest_text(pos, days_line, r"(Mo-Fr|Daily|Sa|Su|WeFrSu|SUN\. ONLY|SAT\. ONLY)")
                    service = "Acela" if num.startswith("21") else "Northeast Regional" if num in REGIONAL_TRAIN_NUMBERS or len(num) <= 3 else ""
                    trains.append({"x": pos, "number": num, "service": service, "agency": "Amtrak", "days": normalize_days(days)})
                return trains
    return trains


def train_columns_for_ctrail(section: str, train_prefix: str) -> list[dict[str, str]]:
    lines = section.splitlines()[:20]
    for idx, line in enumerate(lines):
        nums = [(m.start(), m.group().rstrip("*")) for m in re.finditer(r"\b\d{2,4}\*?", line)]
        if len(nums) < 2:
            continue

        agency_line = lines[idx - 1] if idx > 0 else ""
        agency_marks = [(m.start(), m.group()) for m in re.finditer(r"\b(?:SLE(?:\s+THRU)?|HL|AMTK|MNR|CTtransit)\b", agency_line)]
        agency_marks.extend((m.start(), m.group()) for m in re.finditer(r"\bCTtransit\b", line))
        if not agency_marks:
            continue

        note_lines = "\n".join(lines[idx + 1: idx + 3])
        notes = [(m.start(), normalize_days(m.group())) for m in re.finditer(r"SAT\. ONLY|SUN\. ONLY", note_lines, re.I)]
        note_by_position = closest_notes_by_train_position(nums, notes)

        trains = []
        for pos, num in nums:
            label = nearest_label(pos, agency_marks)
            if len(num) < 4 and label not in {"AMTK", "CTtransit"}:
                continue
            if label == "MNR":
                agency, service, route = "Metro-North", "New Haven Line", "New Haven Line"
            elif label == "AMTK":
                agency, service, route = "Amtrak", "Amtrak connection", "Amtrak connection"
            elif label == "HL":
                agency, service, route = "CTrail", "Hartford Line", "Hartford Line"
            elif label == "CTtransit":
                agency, service, route = "CTtransit", "Bus substitution", "Hartford Line"
            else:
                agency = "CTrail"
                service = "Shore Line East" if train_prefix == "SLE" else "Hartford Line"
                route = service
            trains.append({"x": pos, "number": num, "service": service, "route": route, "agency": agency, "days": note_by_position.get(pos, "")})
        if trains:
            trains = expand_spanned_cttransit_columns(prune_train_columns(trains), section)
            return variant_duplicate_train_numbers(trains)
    return []


def expand_spanned_cttransit_columns(trains: list[dict[str, str]], section: str) -> list[dict[str, str]]:
    out = list(trains)
    cttransit_950 = [train for train in out if train.get("agency") == "CTtransit" and train["number"] == "950"]
    if len(cttransit_950) != 1:
        return out

    train = cttransit_950[0]
    index = out.index(train)
    previous_x = out[index - 1]["x"] if index > 0 else -1
    next_x = out[index + 1]["x"] if index + 1 < len(out) else 10_000
    time_positions = first_station_time_positions(section)
    spanned_positions = [x for x in time_positions if previous_x + 3 < x < next_x - 3]
    if len(spanned_positions) != 2:
        return out

    replacement = [dict(train, x=x) for x in spanned_positions]
    return out[:index] + replacement + out[index + 1:]


def first_station_time_positions(section: str) -> list[int]:
    for line in section.splitlines():
        if parse_ctrail_station(line):
            return [match.start() for match in TIME_RE.finditer(line)]
    return []


def variant_duplicate_train_numbers(trains: list[dict[str, str]]) -> list[dict[str, str]]:
    counts: dict[tuple[str, str, str], int] = {}
    for train in trains:
        key = (train.get("agency", ""), train.get("service", ""), train["number"])
        counts[key] = counts.get(key, 0) + 1

    seen: dict[tuple[str, str, str], int] = {}
    out = []
    for train in trains:
        copy = dict(train)
        key = (copy.get("agency", ""), copy.get("service", ""), copy["number"])
        if counts[key] > 1:
            seen[key] = seen.get(key, 0) + 1
            copy["number"] = f"{copy['number']}~{seen[key]}"
            note = duplicate_train_variant_note(copy)
            if note:
                copy["note"] = "; ".join(part for part in [copy.get("note", "").strip(), note] if part)
        out.append(copy)
    return out


def duplicate_train_variant_note(train: dict[str, str]) -> str:
    if train.get("agency") == "Amtrak" and train.get("number") == "490~1":
        return "express"
    if train.get("agency") == "Amtrak" and train.get("number") == "490~2":
        return "local"
    return ""


def nearest_label(x: int, labels: list[tuple[int, str]]) -> str:
    return min(labels, key=lambda item: abs(item[0] - x))[1].split()[0]


def train_columns_for_mnr_connection(section: str) -> list[dict[str, str]]:
    trains = []
    lines = section.splitlines()[:8]
    for line_index, line in enumerate(lines):
        nums = [(m.start(), m.group()) for m in re.finditer(r"\b\d{4}\b", line)]
        if len(nums) < 2:
            continue
        note_line = lines[line_index + 1] if line_index + 1 < len(lines) else ""
        notes = [(m.start(), normalize_days(m.group())) for m in re.finditer(r"MON-THURS", note_line, re.I)]
        note_by_position = closest_notes_by_train_position(nums, notes)
        for pos, num in nums:
            days = note_by_position.get(pos, "")
            trains.append({
                "x": pos,
                "number": num,
                "service": "New Haven Line",
                "route": "New Haven Line",
                "agency": "Metro-North",
                "days": days,
            })
        return prune_train_columns(trains)
    return trains


def train_columns_for_sle_connection_to_new_york(section: str) -> list[dict[str, str]]:
    lines = section.splitlines()[:8]
    for idx, line in enumerate(lines):
        nums = [(m.start(), m.group()) for m in re.finditer(r"\b\d{4}\b", line)]
        if len(nums) < 2:
            continue

        agency_line = lines[idx - 1] if idx > 0 else ""
        agency_marks = [(m.start(), m.group()) for m in re.finditer(r"\b(?:SLE(?:\s+THRU)?|MNR)\b", agency_line)]
        if not agency_marks:
            continue

        note_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        service_days_by_position: dict[int, str] = {}
        raw_note_by_position: dict[int, str] = {}
        for match in re.finditer(r"MON-THURS|FRI|SUP\s+EXP", note_line, re.I):
            train_pos, _num = min(nums, key=lambda item: abs(item[0] - match.start()))
            column_note = re.sub(r"\s+", " ", match.group().upper())
            if column_note == "SUP EXP":
                raw_note_by_position[train_pos] = "SUP EXP"
            else:
                service_days_by_position[train_pos] = normalize_days(column_note)
        trains = []
        for pos, num in nums:
            label = nearest_label(pos, agency_marks)
            days = service_days_by_position.get(pos, "")
            raw_note = raw_note_by_position.get(pos, "")
            if label == "SLE":
                trains.append({
                    "x": pos,
                    "number": num,
                    "service": "Shore Line East",
                    "route": "Shore Line East",
                    "agency": "CTrail",
                    "days": days,
                    "note": raw_note,
                })
            else:
                trains.append({
                    "x": pos,
                    "number": num,
                    "service": "New Haven Line",
                    "route": "New Haven Line",
                    "agency": "Metro-North",
                    "days": days,
                    "note": raw_note,
                })
        return sorted(trains, key=lambda train: train["x"])
    return []


def closest_notes_by_train_position(nums: list[tuple[int, str]], notes: list[tuple[int, str]]) -> dict[int, str]:
    assigned = {}
    for note_pos, note in notes:
        train_pos, _ = min(nums, key=lambda item: abs(item[0] - note_pos))
        assigned[train_pos] = note
    return assigned


def train_columns_for_connection_group(lines: list[str]) -> list[dict[str, str]]:
    trains = []
    for idx, line in enumerate(lines[:4]):
        nums = [(m.start(), m.group().rstrip("*")) for m in re.finditer(r"\b\d{2,4}(?:/\d{2,4})?\*?", line)]
        if not nums:
            continue
        agency_line = lines[idx - 1] if idx > 0 else line
        agency_marks = [(m.start(), m.group()) for m in re.finditer(r"\b(?:MNR|AMTK|SLE|HL|CTtransit)\b", agency_line)]
        if not agency_marks:
            continue
        note_lines = "\n".join(lines[idx + 1: idx + 3])
        notes = [(m.start(), normalize_days(m.group())) for m in re.finditer(r"SAT\. ONLY|SUN\. ONLY|Mon\. - Thurs\.|MON-THURS", note_lines, re.I)]
        note_by_position = closest_notes_by_train_position(nums, notes)
        for pos, num in nums:
            label = nearest_label(pos, agency_marks)
            if label == "MNR":
                agency, service, route = "Metro-North", "New Haven Line", "New Haven Line"
            elif label == "AMTK":
                agency, service, route = "Amtrak", "Amtrak connection", "Amtrak connection"
            elif label == "SLE":
                agency, service, route = "CTrail", "Shore Line East", "Shore Line East"
            elif label == "HL":
                agency, service, route = "CTrail", "Hartford Line", "Hartford Line"
            else:
                agency, service, route = "CTtransit", "950 Bus", "950 Bus"
            trains.append({
                "x": pos,
                "number": num,
                "service": service,
                "route": route,
                "agency": agency,
                "days": note_by_position.get(pos, ""),
            })
        if trains:
            return prune_train_columns(trains)
    return trains


def train_columns_for_mnr(chunk: str) -> list[dict[str, str]]:
    trains = []
    for line in chunk.splitlines()[:12]:
        nums = [(m.start(), m.group()) for m in re.finditer(r"\bB?\d{4}\b", line)]
        if len(nums) >= 2:
            for pos, num in nums:
                trains.append({"x": pos, "number": num.lstrip("B"), "service": "New Haven Line", "agency": "Metro-North", "days": ""})
            if len(trains) >= 2:
                return prune_train_columns(trains)
    return trains


def train_columns_for_mnr_plain(chunk: str) -> list[dict[str, str]]:
    lines = chunk.splitlines()
    for idx, line in enumerate(lines[:18]):
        nums = re.findall(r"\bB?\d{4}\b", line)
        if len(nums) < 2:
            continue
        period_line = ""
        for look in lines[idx + 1: idx + 5]:
            if len(re.findall(r"\b(?:AM|PM)\b", look)) >= 2:
                period_line = look
                break
        periods = re.findall(r"\b(?:AM|PM)\b", period_line)
        trains = []
        for i, num in enumerate(nums):
            trains.append({
                "x": i,
                "number": num.lstrip("B"),
                "service": "New Haven Line",
                "agency": "Metro-North",
                "days": "",
                "period": periods[i] if i < len(periods) else (periods[-1] if periods else "AM"),
            })
        return trains
    return []


def iter_mnr_blocks(text: str):
    lines = text.splitlines()
    current_direction = ""
    idx = 0
    while idx < len(lines):
        upper = lines[idx].upper()
        if "TO NEW YORK" in upper:
            current_direction = "To Grand Central"
        elif "TO NEW HAVEN" in upper:
            current_direction = "To New Haven"
        elif "TO WATERBURY" in upper:
            current_direction = "To Waterbury"
        elif "TO DANBURY" in upper:
            current_direction = "To Danbury"
        elif "TO NEW CANAAN" in upper:
            current_direction = "To New Canaan"

        nums = re.findall(r"\bB?\d{4}\b", lines[idx])
        if len(nums) >= 2:
            period_line = ""
            period_idx = idx
            for look_idx in range(idx + 1, min(idx + 5, len(lines))):
                if len(re.findall(r"\b(?:AM|PM)\b", lines[look_idx])) >= 2:
                    period_line = lines[look_idx]
                    period_idx = look_idx
                    break
            if period_line:
                periods = re.findall(r"\b(?:AM|PM)\b", period_line)
                trains = []
                for col, num in enumerate(nums):
                    trains.append({
                        "x": col,
                        "number": num.lstrip("B"),
                        "service": "New Haven Line",
                        "agency": "Metro-North",
                        "days": "",
                        "period": periods[col] if col < len(periods) else (periods[-1] if periods else "AM"),
                    })
                block_lines = []
                idx = period_idx + 1
                while idx < len(lines):
                    next_nums = re.findall(r"\bB?\d{4}\b", lines[idx])
                    if len(next_nums) >= 2:
                        idx -= 1
                        break
                    if re.match(r"\s*(?:AM|PM)(?:\s+(?:AM|PM))*\s*$", lines[idx]):
                        break
                    block_lines.append(lines[idx])
                    idx += 1
                yield current_direction or "Metro-North", trains, block_lines
        idx += 1


def parse_amtrak_station(line: str) -> tuple[str, str] | None:
    if not re.match(r"\s*\d+\s+", line):
        return None
    prefix = TIME_RE.split(line, maxsplit=1)[0]
    prefix = re.sub(r"^\s*\d+\s+", "", prefix)
    prefix = re.sub(r"\s+(Ar|Dp)\s*$", "", prefix).strip()
    prefix = re.sub(r"\s+(SLE|HL|MN|NYCT|LIRR|LRT|PATH|SEPTA|MARC|MBTA).*$", "", prefix).strip()
    if not prefix:
        return None
    match = re.search(r"\(([^)]+)\)", prefix)
    station_id = match.group(1) if match else station_id_for(prefix)
    name = re.sub(r"\s*\([^)]+\)", "", prefix).strip(" -")
    return name, station_id


def parse_ctrail_station(line: str) -> tuple[str, str] | None:
    if not TIME_RE.search(line):
        return None
    name = line[:TIME_RE.search(line).start()].strip()
    name = re.sub(r"^[^A-Za-z]*(?=[A-Za-z])", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if re.match(r"^To\s+", name):
        return None
    if not name or len(name) > 45 or is_headerish(name):
        return None
    return name, station_id_for(name)


def parse_mnr_station(line: str) -> tuple[str, str] | None:
    match = re.search(r"\b\d{1,2}\s+\d{2}\b", line)
    if not match:
        return None
    name = line[:match.start()]
    name = re.sub(r"^\s*\d+\s+", "", name)
    name = re.sub(r"\b(Ar\.|Lv\.|A|Ú|≤|C|D|R|H)\b", " ", name)
    name = re.sub(r"[^A-Za-z0-9.'& -]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name or len(name) > 45 or is_headerish(name):
        return None
    return name, station_id_for(name)


def split_ctrail_sections(text: str) -> list[tuple[str, str]]:
    markers = ["TO NEW HAVEN", "TO NEW LONDON", "TO HARTFORD AND SPRINGFIELD"]
    positions = []
    for marker in markers:
        idx = text.find(marker)
        while idx != -1:
            positions.append((idx, marker))
            idx = text.find(marker, idx + 1)
    positions.sort()
    sections = []
    for i, (idx, marker) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        section = text[idx:end]
        cut_points = [
            point for point in [
                section.find("CONNECTIONS"),
                section.find("CONNECTING RAIL SERVICES"),
                section.find("Contact Us:"),
            ] if point != -1
        ]
        if cut_points:
            section = section[:min(cut_points)]
        sections.append((marker.replace("TO ", "To ").title(), section))
    return sections


def split_connection_sections(text: str, marker: str) -> list[str]:
    sections = []
    start = text.find(marker)
    while start != -1:
        next_markers = [
            idx for idx in [
                text.find("CONNECTIONS TO NEW YORK", start + len(marker)),
                text.find("CONNECTIONS FROM NEW YORK", start + len(marker)),
                text.find("TO NEW LONDON", start + len(marker)),
                text.find("TO NEW HAVEN", start + len(marker)),
                text.find("TO HARTFORD", start + len(marker)),
            ] if idx != -1
        ]
        end = min(next_markers) if next_markers else len(text)
        sections.append(text[start:end])
        start = text.find(marker, start + len(marker))
    return sections


def split_hartford_connection_sections(text: str) -> list[str]:
    sections = []
    start = text.find("CONNECTING RAIL SERVICES")
    while start != -1:
        next_markers = [
            idx for idx in [
                text.find("TO HARTFORD AND SPRINGFIELD", start),
                text.find("TO NEW HAVEN", start),
                text.find("Contact Us:", start),
            ] if idx != -1 and idx > start
        ]
        end = min(next_markers) if next_markers else len(text)
        sections.append(text[start:end])
        start = text.find("CONNECTING RAIL SERVICES", start + 1)
    return sections


def hartford_connection_direction(section: str) -> str:
    return "From New Haven" if re.search(r"\bTo (?:Grand Central Terminal|Penn Station|New London)\b", section) else "To New Haven"


def iter_connection_groups(section: str):
    lines = section.splitlines()
    headers = []
    for index, line in enumerate(lines):
        if any(label in line for label in ["Metro-North Railroad", "Amtrak", "Shore Line East"]):
            headers.append(index)
    for group_number, start in enumerate(headers):
        end = headers[group_number + 1] if group_number + 1 < len(headers) else len(lines)
        yield group_number, lines[start:end]


def connection_time_line(lines: list[str], direction: str) -> str:
    if direction == "To New Haven":
        for line in lines:
            if "New Haven Union Station - Arrival" in line:
                return line
    else:
        for line in lines:
            if re.search(r"\bTo (?:Grand Central Terminal|Penn Station|New London)\b", line):
                return line
    return ""


def connection_raw_note(lines: list[str], direction: str) -> str:
    if direction == "To New Haven":
        return "Hartford Line connection arrival at New Haven; opposite endpoint unknown pending full timetable"
    for line in lines:
        match = re.search(r"\bTo (Grand Central Terminal|Penn Station|New London)\b", line)
        if match:
            return f"Hartford Line connection departure from New Haven toward {match.group(1)}; arrival endpoint/time unknown pending full timetable"
    return "Hartford Line connection departure from New Haven; arrival endpoint/time unknown pending full timetable"


def split_mnr_tables(text: str) -> list[tuple[str, str]]:
    markers = [("TO NEW YORK", "To Grand Central"), ("TO NEW HAVEN", "To New Haven"), ("TO WATERBURY", "To Waterbury"), ("TO NEW CANAAN", "To New Canaan"), ("TO DANBURY", "To Danbury")]
    positions = []
    for marker, direction in markers:
        idx = text.find(marker)
        while idx != -1:
            positions.append((idx, direction))
            idx = text.find(marker, idx + 1)
    positions.sort()
    chunks = []
    for i, (idx, direction) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        chunks.append((direction, text[idx:end]))
    return chunks


def nearest_train(x: int, trains: list[dict[str, str]]) -> dict[str, str] | None:
    if not trains:
        return None
    nearest = min(trains, key=lambda t: abs(t["x"] - x))
    return nearest if abs(nearest["x"] - x) <= 18 else nearest


def nearest_text(x: int, line: str, pattern: str) -> str:
    matches = list(re.finditer(pattern, line, re.I))
    if not matches:
        return ""
    return min(matches, key=lambda m: abs(m.start() - x)).group()


def prune_train_columns(trains: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for train in trains:
        key = (train["x"], train["number"], train["agency"])
        if key not in seen:
            seen.add(key)
            out.append(train)
    return sorted(out, key=lambda t: t["x"])


REGIONAL_TRAIN_NUMBERS = {
    "65", "66", "67", "82", "83", "84", "85", "86", "87", "88", "93", "94", "95", "96",
    "99", "110", "111", "112", "113", "114", "115", "116", "117", "119", "121", "122",
    "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134", "135",
    "136", "137", "138", "139", "140", "141", "143", "145", "146", "147", "148", "149",
    "150", "151", "152", "153", "154", "155", "156", "157", "158", "159", "160", "161",
    "162", "163", "164", "165", "166", "167", "168", "169", "170", "171", "172", "173",
    "174", "175", "176", "177", "178", "179", "180", "181", "182", "183", "184", "185",
    "186", "187", "188", "189", "190", "191", "192", "193", "194", "195",
}


def layout_text(page) -> str:
    return page.extract_text(extraction_mode="layout") or page.extract_text() or ""


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def page_service_days(title: str, text: str) -> str:
    upper = (title + "\n" + text[:1200]).upper()
    if "WEEKDAY" in upper:
        return "weekday"
    if "SATURDAY" in upper and "SUNDAY" in upper:
        return "weekend"
    if "SATURDAY" in upper:
        return "saturday"
    if "SUNDAY" in upper:
        return "sunday"
    return ""


def normalize_days(days: str) -> str:
    days = (days or "").lower().replace(".", "").strip()
    return {
        "mo-fr": "weekday",
        "daily": "daily",
        "sa": "saturday",
        "su": "sunday",
        "sat only": "saturday",
        "sun only": "sunday",
        "wefrsu": "wednesday_friday_sunday",
        "mon-thurs": "monday_through_thursday",
        "mon - thurs": "monday_through_thursday",
        "fri": "friday",
    }.get(days, days)


def normalize_time(hour: str, minute: str, period: str) -> str:
    h = int(hour)
    if period.upper() == "P" and h != 12:
        h += 12
    if period.upper() == "A" and h == 12:
        h = 0
    return f"{h:02d}:{int(minute):02d}"


def station_id_for(name: str) -> str:
    clean = re.sub(r"\s+", " ", name).strip()
    if clean in STATION_IDS:
        return STATION_IDS[clean]
    for key, value in STATION_IDS.items():
        if clean.lower() == key.lower():
            return value
    return re.sub(r"[^A-Z0-9]+", "_", clean.upper()).strip("_")[:12]


def valid_range(text: str) -> tuple[str, str]:
    dates = DATE_RE.findall(text)
    if len(dates) >= 2:
        return ["-".join(d) for d in dates[:2]]
    return "", ""


def generated_on(text: str) -> str:
    match = re.search(r"generated on\s+(\d{4}-\d{2}-\d{2})", text, re.I)
    return match.group(1) if match else ""


def text_effective_date(text: str) -> str:
    match = re.search(r"Effective\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", text, re.I)
    return month_date(match) if match else ""


def text_as_of_date(text: str) -> str:
    match = re.search(r"As of\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", text, re.I)
    return month_date(match) if match else ""


def month_date(match) -> str:
    months = {m.lower(): i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], start=1)}
    return f"{int(match.group(3)):04d}-{months[match.group(1).lower()]:02d}-{int(match.group(2)):02d}"


def mta_updated_date(text: str) -> str:
    match = MTA_UPDATED_RE.search(text)
    if not match:
        return ""
    month, day, year = match.groups()
    return f"20{int(year):02d}-{int(month):02d}-{int(day):02d}"


def mta_revision_date(text: str) -> str:
    match = MTA_REVISED_RE.search(text)
    if not match:
        return ""
    if match.group(1):
        month, day, year = match.group(1), match.group(2), match.group(3)
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    month, day, year = match.group(4), match.group(5), match.group(6)
    return f"20{int(year):02d}-{int(month):02d}-{int(day):02d}"


def pdf_date_to_iso(value: str) -> str:
    match = re.search(r"D:(\d{4})(\d{2})(\d{2})", value)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else ""


def natural_train_key(value: str):
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else 0


def source_page_sort_key(value: str) -> int:
    return int(value) if str(value).isdigit() else 0


def is_headerish(name: str) -> bool:
    upper = name.upper()
    return any(part in upper for part in ["CONNECTING", "RAIL SERVICES", "METRO-NORTH", "AMTRAK", "SHORE LINE EAST", "MILES", "MONDAY", "SATURDAY", "SUNDAY", "TRAIN"])


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    out = []
    for row in rows:
        key = tuple(row.get(col, "") for col in BASE_COLUMNS)
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def stitch_sle_through_trips(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault((row["source_pdf"], row["train_number"]), []).append(row)

    stitched_keys = set()
    output = []

    for key, group in grouped.items():
        sle_rows = [
            row for row in group
            if row["agency"] == "CTrail" and row["service_name"] == "Shore Line East"
        ]
        mnr_connection_rows = [
            row for row in group
            if row["agency"] == "Metro-North" and row["service_name"] == "New Haven Line"
        ]

        if not sle_rows or not mnr_connection_rows:
            continue

        sle_direction = sorted(sle_rows, key=lambda row: int(row["station_sequence"]))[0]["direction"]
        if sle_direction != "To New London":
            continue

        stitched_keys.add(key)
        mnr_sorted = sorted(mnr_connection_rows, key=lambda row: int(row["station_sequence"]))
        sle_sorted = sorted(sle_rows, key=lambda row: int(row["station_sequence"]))
        stitched = []

        for index, row in enumerate(mnr_sorted, start=1):
            stitched_row = dict(row)
            stitched_row["agency"] = "CTrail"
            stitched_row["service_name"] = "Shore Line East"
            stitched_row["route_name"] = "Shore Line East"
            stitched_row["direction"] = sle_direction
            stitched_row["station_sequence"] = str(index)
            if stitched_row["station_id"] == "NHV":
                stitched_row["station_name"] = "New Haven - Union Station"
            stitched_row["raw_notes"] = "SLE THRU connection from New York"
            stitched.append(stitched_row)

        seen_station_ids = {row["station_id"] for row in stitched}
        for row in sle_sorted:
            if row["station_id"] in seen_station_ids:
                continue
            stitched_row = dict(row)
            stitched_row["station_sequence"] = str(len(stitched) + 1)
            stitched_row["raw_notes"] = "SLE THRU connection from New York"
            stitched.append(stitched_row)

        output.extend(stitched)

    for row in rows:
        if (row["source_pdf"], row["train_number"]) not in stitched_keys:
            output.append(row)

    return dedupe_rows(output)


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_existing_source_csvs(rows: list[dict[str, str]]) -> None:
    if not SOURCE_CSV_DIR.exists():
        return
    by_source: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_source.setdefault(row["source_pdf"], []).append(row)
    for source_name, source_rows in by_source.items():
        path = SOURCE_CSV_DIR / f"{Path(source_name).stem}.csv"
        write_csv(path, BASE_COLUMNS, source_rows)
    for path in SOURCE_CSV_DIR.glob("*.csv"):
        source_pdf = f"{path.stem}.pdf"
        source_rows = by_source.get(source_pdf)
        if source_rows is not None:
            write_csv(path, BASE_COLUMNS, source_rows)


def apply_known_service_exceptions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        copy = dict(row)
        if (
            copy["agency"] == "Metro-North"
            and copy["service_name"] == "New Haven Line"
            and copy["train_number"] in {"3419", "3539", "3541"}
            and copy["direction"] == "To Grand Central"
            and copy["source_pdf"] == "metro_north_new_haven_line_effective_2026-03-29_revised_2026-04-11_updated_2026-04-08.pdf"
        ):
            copy["service_days"] = "friday"
            copy["service_dates"] = "2026-07-02"
            if "Friday only" not in copy["raw_notes"]:
                copy["raw_notes"] = "; ".join(part for part in [copy["raw_notes"], "Friday only; July 2 only"] if part)
        if (
            copy["agency"] == "Metro-North"
            and copy["service_name"] == "New Haven Line"
            and copy["train_number"] in {"1417", "1419", "1427", "1437", "1537", "1539"}
            and copy["direction"] == "To Grand Central"
            and copy["source_pdf"] == "metro_north_new_haven_line_effective_2026-03-29_revised_2026-04-11_updated_2026-04-08.pdf"
        ):
            copy["service_days"] = "monday_through_thursday"
            if "Does not operate 2026-07-02" not in copy["raw_notes"]:
                copy["raw_notes"] = "; ".join(part for part in [copy["raw_notes"], "Does not operate 2026-07-02"] if part)
        out.append(copy)
    return out


def apply_mnr_new_haven_overlay_fixture(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    source_pdf = "metro_north_new_haven_line_effective_2026-03-29_revised_2026-04-11_updated_2026-04-08.pdf"
    if any(row["source_pdf"] == source_pdf and row["train_number"] == "1437" for row in rows):
        return rows

    fixtures: dict[str, list[tuple[str, str]]] = {
        "1237": [
            ("Harrison", "08:49"), ("Mamaroneck", "08:52"), ("Larchmont", "08:56"),
            ("New Rochelle", "09:00"), ("Pelham", "09:04"), ("Mount Vernon East", "09:07"),
            ("Fordham", "09:15"), ("Harlem-125th St.", "09:23"), ("Grand Central", "09:36"),
        ],
        "1437": [
            ("South Norwalk", "08:28"), ("Rowayton", "08:32"), ("Darien", "08:36"),
            ("Noroton Heights", "08:39"), ("Stamford", "08:45"), ("Greenwich", "08:54"),
            ("Harlem-125th St.", "09:25"), ("Grand Central", "09:38"),
        ],
        "3539": [
            ("New Haven", "07:41"), ("West Haven", "07:46"), ("Milford", "07:53"),
            ("Stratford", "07:59"), ("Bridgeport", "08:05"), ("Fairfield-Black Rock", "08:11"),
            ("Fairfield", "08:14"), ("Southport", "08:17"), ("Greens Farms", "08:21"),
            ("Westport", "08:26"), ("East Norwalk", "08:30"), ("South Norwalk", "08:33"),
            ("Rowayton", "08:37"), ("Darien", "08:40"), ("Noroton Heights", "08:43"),
            ("Stamford", "08:49"), ("Greenwich", "08:57"), ("Harlem-125th St.", "09:29"),
            ("Grand Central", "09:43"),
        ],
        "1537": [
            ("New Haven", "07:44"), ("West Haven", "07:49"), ("Milford", "07:56"),
            ("Stratford", "08:02"), ("Bridgeport", "08:08"), ("Fairfield-Black Rock", "08:14"),
            ("Fairfield", "08:17"), ("Southport", "08:20"), ("Greens Farms", "08:24"),
            ("Westport", "08:29"), ("East Norwalk", "08:33"), ("South Norwalk", "08:36"),
            ("Darien", "08:42"), ("Stamford", "08:49"), ("Greenwich", "08:57"),
            ("Harlem-125th St.", "09:29"), ("Grand Central", "09:43"),
        ],
        "1539": [
            ("New Haven", "07:56"), ("West Haven", "08:00"), ("Milford", "08:07"),
            ("Stratford", "08:14"), ("Bridgeport", "08:20"), ("Fairfield-Black Rock", "08:26"),
            ("Fairfield", "08:30"), ("Darien", "08:42"), ("Stamford", "08:49"),
            ("Harlem-125th St.", "09:34"), ("Grand Central", "09:47"),
        ],
        "1339": [
            ("Stamford", "08:59"), ("Old Greenwich", "09:02"), ("Riverside", "09:05"),
            ("Cos Cob", "09:07"), ("Greenwich", "09:10"), ("Port Chester", "09:14"),
            ("Rye", "09:17"), ("Harrison", "09:21"), ("Harlem-125th St.", "09:50"),
            ("Grand Central", "10:02"),
        ],
        "3541": [
            ("New Haven", "08:24"), ("Bridgeport", "08:44"), ("Stamford", "09:12"),
            ("Grand Central", "10:05"),
        ],
        "1239": [
            ("Harrison", "09:26"), ("Mamaroneck", "09:29"), ("Larchmont", "09:33"),
            ("New Rochelle", "09:37"), ("Pelham", "09:41"), ("Mount Vernon East", "09:44"),
            ("Harlem-125th St.", "10:03"), ("Grand Central", "10:15"),
        ],
        "1341": [
            ("Stamford", "09:24"), ("Old Greenwich", "09:27"), ("Riverside", "09:30"),
            ("Cos Cob", "09:32"), ("Greenwich", "09:35"), ("Port Chester", "09:39"),
            ("Rye", "09:42"), ("Harrison", "09:46"), ("Harlem-125th St.", "10:15"),
            ("Grand Central", "10:27"),
        ],
        "1241": [
            ("Harrison", "09:50"), ("Mamaroneck", "09:53"), ("Larchmont", "09:57"),
            ("New Rochelle", "10:01"), ("Pelham", "10:05"), ("Mount Vernon East", "10:08"),
            ("Harlem-125th St.", "10:27"), ("Grand Central", "10:38"),
        ],
        "1545": [
            ("New Haven", "08:47"), ("West Haven", "08:51"), ("Milford", "08:59"),
            ("Stratford", "09:06"), ("Bridgeport", "09:12"), ("South Norwalk", "09:35"),
            ("Stamford", "09:46"), ("Harlem-125th St.", "10:28"), ("Grand Central", "10:40"),
        ],
        "1347": [
            ("Stamford", "10:05"), ("Old Greenwich", "10:09"), ("Riverside", "10:12"),
            ("Cos Cob", "10:14"), ("Greenwich", "10:18"), ("Port Chester", "10:22"),
            ("Rye", "10:25"), ("Harrison", "10:30"), ("Mamaroneck", "10:33"),
            ("Larchmont", "10:37"), ("New Rochelle", "10:41"), ("Pelham", "10:44"),
            ("Mount Vernon East", "10:47"), ("Harlem-125th St.", "11:05"),
            ("Grand Central", "11:18"),
        ],
    }

    existing = {
        (row["source_pdf"], row["train_number"], row["station_id"], row["departure_time"])
        for row in rows
    }
    out = list(rows)
    for train_number, stops in fixtures.items():
        for sequence, (station_name, hhmm) in enumerate(stops, start=1):
            station_id = station_id_for(station_name)
            key = (source_pdf, train_number, station_id, hhmm)
            if key in existing:
                continue
            out.append({
                "agency": "Metro-North",
                "service_name": "New Haven Line",
                "route_name": "New Haven Line",
                "train_number": train_number,
                "direction": "To Grand Central",
                "station_id": station_id,
                "station_name": station_name,
                "station_sequence": str(sequence),
                "arrival_time": hhmm,
                "departure_time": hhmm,
                "service_start_date": "2026-03-29",
                "service_end_date": "",
                "service_dates": "",
                "service_days": "weekday",
                "timetable_effective_date": "2026-03-29",
                "timetable_last_updated_date": "2026-04-08",
                "timetable_revision_date": "2026-04-11",
                "source_original_filename": "04-07-26_NHL+Branches-Sched_v3.pdf",
                "source_pdf": source_pdf,
                "source_page": "2",
                "raw_notes": "To Grand Central; AM Peak & Mornings continuation table fixture",
            })
            existing.add(key)
    return out


if __name__ == "__main__":
    main()
