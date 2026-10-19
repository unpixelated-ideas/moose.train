# Search schedule for GitHub Pages

The browser loads `supporting_files/assets/schedule/search.json.gz`, a prebuilt
table of the exact trips produced by the existing CSV processing code. Repeated
strings are stored once and rows share field names. The browser decompresses the
file explicitly, so GitHub Pages does not need custom compression headers.
Browsers without `DecompressionStream` load `search.json`. If optimized files
cannot load, the existing CSV loader remains available.

Loading starts after the initial page has a chance to paint, or on station field
focus. A search shares the same loading promise. Prepared trips remain in memory
for subsequent searches; persistent browser database caching is not implemented.

## Updating schedules

After changing the compressed snapshot `moose_train_schedule.csv.gz` or the trip preparation functions in
`index.html`, run with Node.js 22 or newer:

```sh
node supporting_files/scripts/build_search_schedule.js
node supporting_files/scripts/build_search_schedule.js --check
node supporting_files/tests/compact_schedule.test.js
```

Commit `index.html` and both generated files along with the schedule snapshot changes.
The builder updates the asset version in `index.html` to prevent reusing an old
schedule from the browser cache. It checks every decoded trip and metadata entry
against the CSV-derived result, preserving service dates, overnight stop times,
trip identities, inferred stops, and duplicate removal. No npm packages required.

The check command fails if the committed assets are stale. The GitHub Actions
`Check search schedule` workflow also runs this check on relevant pushes and pull
requests (it does not deploy or block the existing Pages deployment). Publish these files
through the site's existing GitHub Pages process; no hosting changes required.

## Compressed repository snapshot

The complete schedule is stored losslessly as `moose_train_schedule.csv.gz` to stay below GitHub’s per-file limit. The builder reads that snapshot directly, with legacy plaintext CSV accepted when no compressed snapshot exists. The extractor writes deterministic gzip snapshots; the publication packager restores `moose_train_schedule.csv` for existing public download and fallback URLs. A local preview can also load the compressed CSV fallback directly. Metro-North per-feed CSV downloads use `.csv.gz` because the full feed also exceeds the file limit. No CSV columns, service dates, source identities, or train times are discarded.
