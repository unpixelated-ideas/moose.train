# Project Workflows

## Project Architecture

- **Read** the [project snapshot](00_project_snapshot.md), [source PDF notes](../source_pdfs/README.md), [extraction summary](../extraction/extraction_summary.csv), [extraction logic](../reference/extraction_logic.md), and [routing logic](../reference/routing_logic.md).
- **Scope** changes by area and record cross-cutting decisions in the project snapshot. Keep supporting material under `supporting_files/`.
- **Verify** that the snapshot reflects the current data sources, known limitations, and affected areas.

## Timetable Extraction

- **Read** the [extraction handoff](01_extraction_handoff.md), [extraction logic](../reference/extraction_logic.md), [source PDF notes](../source_pdfs/README.md), and [extractor](../extraction/extract_timetables.py).
- **Maintain** source PDF ingestion, filename normalization, the extraction summary, and the compressed schedule. Preserve source filenames and page references in the output.
- **Verify** the extraction summary and source traceability. Check Metro-North coordinate parsing and branch classification, including Danbury service after any Metro-North source change.

## Routing

- **Read** the [routing handoff](02_routing_handoff.md), [routing logic](../reference/routing_logic.md), and the route search implementation in [index.html](../../index.html).
- **Maintain** direct and transfer searches, transfer constraints, service-day applicability, unknown-time handling, and result ordering.
- **Verify** representative direct and transfer searches. Trace failures to the schedule rows before changing extraction logic.

## Frontend and Localization

- **Read** the [frontend and localization handoff](03_frontend_i18n_handoff.md) and [index.html](../../index.html).
- **Maintain** the layout, result cards, time formatting, English, Korean, and Spanish strings, Korean station names, and the local schedule fallback.
- **Verify** the affected flow in all three languages, including station names, time formatting, and fallback behavior.

## Data Quality and Regression Checks

- **Read** the [data QA handoff](04_data_qa_handoff.md), [extraction summary](../extraction/extraction_summary.csv), [extraction logic](../reference/extraction_logic.md), and [routing logic](../reference/routing_logic.md).
- **Run** fixture checks, invalid-time scans, branch leakage checks, representative route searches, and source traceability checks.
- **Record** failures with the affected CSV rows, train numbers, and source PDFs and pages where available.
