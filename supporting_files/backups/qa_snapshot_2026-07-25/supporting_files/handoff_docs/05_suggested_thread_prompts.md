# Suggested Thread Prompts

Use these prompts to start focused future threads without dragging the whole conversation along.

## Project Control / Architecture Thread

```text
You are taking over project-control work for moose.train. Start by reading supporting_files/handoff_docs/00_project_snapshot.md, supporting_files/source_pdfs/README.md, supporting_files/extraction/extraction_summary.csv, and the two reference docs in supporting_files/reference/. Keep the root folder clean: only index.html, moose_train_schedule.csv, and supporting_files/. Your role is to track current state, known caveats, and decide which specialized thread should own new work. Do not make implementation changes unless explicitly asked.
```

## Timetable Extraction Thread

```text
You are taking over extraction work for moose.train. Start by reading supporting_files/handoff_docs/01_extraction_handoff.md, supporting_files/reference/extraction_logic.md, supporting_files/source_pdfs/README.md, and supporting_files/extraction/extract_timetables.py. Own PDF ingestion, source PDF renaming, extraction_summary.csv, and moose_train_schedule.csv regeneration. Preserve traceability fields. Be especially careful with Metro-North coordinate parsing and branch PDF misclassification. Danbury Branch is currently represented; verify it separately after any Metro-North source changes.
```

## Routing Logic Thread

```text
You are taking over routing logic for moose.train. Start by reading supporting_files/handoff_docs/02_routing_handoff.md and supporting_files/reference/routing_logic.md, then inspect the route logic in index.html. Own direct/transfer search behavior, transfer sanity rules, service-day applicability, unknown-time handling, and route result ordering. Do not modify extraction logic unless a routing bug proves to be caused by bad source data.
```

## Frontend / I18n Thread

```text
You are taking over frontend and localization work for moose.train. Start by reading supporting_files/handoff_docs/03_frontend_i18n_handoff.md, then inspect index.html. Own UI layout, result cards, time-format display, English/Korean/Spanish strings, Korean station display, and local embedded CSV fallback behavior. Avoid changing moose_train_schedule.csv or extraction logic unless explicitly asked.
```

## Data QA / Regression Thread

```text
You are taking over data QA for moose.train. Start by reading supporting_files/handoff_docs/04_data_qa_handoff.md, supporting_files/extraction/extraction_summary.csv, supporting_files/reference/extraction_logic.md, and supporting_files/reference/routing_logic.md. Own fixture checks, invalid-time scans, branch leakage checks, route sanity searches, and source traceability checks. Report issues with exact CSV rows, train numbers, source PDFs, and source pages when possible.
```
