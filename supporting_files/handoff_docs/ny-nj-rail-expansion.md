# New York and New Jersey rail expansion

## Status

The expanded schedule, search page, departure board, and standalone board fallback are together in the working tree. The build covers scheduled Amtrak and NJ Transit commuter rail stops in both states and preserves the existing search area elsewhere. The public site has not been deployed from this working tree.

- The November source snapshots yield 40,933 prepared trips, up from 38,083. All 468,778 preexisting trip-stop signatures matched on service, train, service dates, station, times, and boarding restrictions.
- The NJ Transit importer covers 163 distinct canonical stations across 12 commuter rail products, including the event-dependent Meadowlands service. It excludes 63 Port Jervis and 39 Gladstone replacement-bus itineraries from the saved feed. The Atlantic City train's Philadelphia terminal remains its destination, outside the search area.
- New Rochelle and New Brunswick share their existing station IDs across operators. The summer Amtrak archive verified the seven Berkshire Flyer stops in New York and both State Fair services. These trips appear when the official feed supplies dates. No historical summer dates were published as current service.
- Search and the board share a generated railroad qualifier map. The two Middletowns retain state qualifiers. Legacy Madison, Murray Hill, and Westport board links resolve to their original stations. New stations have Korean names on both surfaces.
- Search indexes trips by station. The board shares one decoded schedule across initial load and station operations, and conditional refresh reuses it when the server returns HTTP 304. Hosted search and board passed the uncompressed fallback check, and the standalone board opened the expanded embedded schedule.
- The fare request set is still limited to the reviewed station titles. New-station fares use the existing unavailable state until verified. The scheduled deployment workflow refreshes the verified fare snapshot as before.
- The main pages and some existing tests already had working-tree edits before expansion. Those edits were retained. There is no deployment or commit from this session.

## Browser performance

P95 in milliseconds. The baseline used 12 samples per profile. Mobile uses 4× CPU slowdown, 100 ms latency, and 5 Mbps download. The expanded desktop rerun used 24 samples after one 102 ms repeat-search sample in the first 12-sample run. The desktop rerun and mobile comparison meet the 10% release threshold. The desktop rerun still had a 74 ms maximum repeat search, with p95 at 30 ms.

| Profile | Build | First search | Repeat search | Board open | Board station change | Board refresh |
|---|---|---:|---:|---:|---:|---:|
| Desktop | Baseline | 672 | 55 | 1,171 | 20 | 467 |
| Desktop | Expanded rerun | 670 | 30 | 635 | 7 | 17 |
| Throttled mobile | Baseline | 7,280 | 244 | 11,461 | 131 | 4,457 |
| Throttled mobile | Expanded | 7,539 | 110 | 10,433 | 33 | 139 |

Reproduce with `supporting_files/tests/rail_performance.browser.js`. Set `TEST_URL` for the preview, `TEST_SAMPLES` for sample count, and optionally `TEST_PROFILE=desktop` or `mobile`. The baseline and samples from this session are also in `/tmp/moose-rail-baseline.json`, `/tmp/moose-rail-expanded.json`, and `/tmp/moose-rail-expanded-desktop.json` while scratch persists.

## Verification and release

- Python extraction suite passed all 63 tests and the expanded snapshot passed the refresh validator.
- Chrome route regressions, duplicate station IDs and links, Korean board label, hosted uncompressed fallback, and standalone gzip fallback passed using `supporting_files/tests/rail_expansion.browser.test.js`.
- The generated schedule check, 29 nonbrowser JavaScript test files, and the Chrome language and NJ Transit fare tests passed. The fare browser fixture refreshes its timestamp for the test and selects a route eligible for the verified fare. The narrow-screen fare tooltip stays inside the viewport.
- Local publication packaging succeeded with search, departures, and fallback assets. The package is approximately 905 MiB.
- Release through the existing GitHub Pages workflow after reviewing the working tree. The workflow downloads fresh feeds, refreshes fares, checks all required services, and builds both surfaces in one artifact. Verify the public search and board after the deployment completes.
- Run Node and Playwright locally from `/Applications/ChatGPT.app/Contents/Resources/cua_node` with `lib/node_modules` on `NODE_PATH`. CI uses Python 3.12 and the repository pins. The local Python 3.9 verification used `PYTHONPATH=/tmp/moose-expansion-python` with pdfplumber 0.11.7 for compatibility.
