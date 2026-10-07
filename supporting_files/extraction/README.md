# Extraction Workspace

Use this folder for extraction scripts, intermediate tables, OCR notes, QA logs, and generated diagnostics.

After generating a new schedule CSV, rebuild the browser search assets before
publishing: `node supporting_files/scripts/build_search_schedule.js` from the
project root. See [the search build guide](../reference/search_schedule_build.md).

The project root should stay limited to:

- `index.html`
- `moose_train_schedule.csv`
- `supporting_files/`
