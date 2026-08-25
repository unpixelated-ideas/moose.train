# Frontend And I18n Thread Handoff

## Current State

The UI is a single-file local prototype in `index.html`.

Current UI features:

- Origin station input.
- Destination station input.
- Date input.
- Leave-after / arrive-by mode.
- Time format toggle: AM/PM default or 24-hour.
- Language toggle: English, Korean, Spanish.
- Results cards with direct/transfer labels.
- Embedded CSV fallback for local file loading.

## Owned Responsibilities

This thread owns:

- HTML layout and CSS.
- Search form behavior.
- Result card presentation.
- Time formatting.
- Language strings.
- Korean station display.
- Embedded CSV refresh after data changes, when coordinated with extraction.

## Localization Rules

English is the default.

Korean:

- Keep proper nouns in English but append Hangul in parentheses for displayed station names.
- Example: `Old Saybrook (올드 세이브룩)`.
- Origin/destination suggestions should also show English plus Hangul in Korean mode.
- Time and duration strings should be localized.

Spanish:

- Station names remain English.
- Time and duration strings should be localized.
- Ride status labels should be localized.

## Known Pitfalls

- Native `type="time"` inputs can ignore the app's time-format toggle. The current time field is text-controlled.
- Datalist display labels are localized, but search matching must strip parenthetical Hangul.
- Result source PDF/page text is intentionally hidden while preserving visual spacing.
- Do not accidentally delete the second script in `index.html` when refreshing embedded CSV.

## First Checks To Run

Check:

- English, Korean, Spanish language toggles.
- AM/PM and 24-hour time toggle.
- Korean station suggestions for `Old Saybrook`, `Waterbury`, `New Canaan`.
- Result cards in Korean and Spanish include localized status, time range, and duration.

## References

- `index.html`
- `supporting_files/reference/station_aliases.csv`

