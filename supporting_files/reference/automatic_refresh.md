# Daily schedule refresh

`Refresh schedules and publish` runs daily at 7 a.m. America/New_York,
including daylight saving changes. GitHub may delay scheduled jobs.
Actions → Refresh schedules and publish → Run workflow on main starts an
on-demand refresh. All deployments share a concurrency lock.

## One-time activation

Publish the workflow and its helper scripts to main. In the repository's
Settings → Pages → Build and deployment, choose **GitHub Actions** as Source.
Run the workflow manually and confirm both build and deploy jobs succeed.
The repository must remain public; the workflow skips private repositories
and uses only free standard GitHub-hosted runners. No paid services, API keys,
or personal tokens are required.

## Publication behavior

Scheduled, manual, and push runs download all configured GTFS feeds, generate the CSV,
validate all six products and service coverage, and rebuild and test search
assets. It also prepares NJ Transit adult fare snapshots from the free public
planner; unsupported or uncorroborated prices remain unavailable. Only a successful build is deployed. Failure leaves the existing
deployment available; GitHub Actions shows the failure, with notifications
controlled by your GitHub notification preferences.

Daily outputs are deployed as a Pages artifact, not committed back to Git.
The repository therefore remains the manually maintained baseline. Every
push to main downloads and validates fresh agency feeds before publishing
the site edits, so a code update cannot republish the older saved baseline.
If a refresh or validation fails, the code update is not deployed and the
existing live site stays available.
Source CSV downloads are included in the deployment; raw GTFS ZIPs and backups
are excluded. Artifacts expire after one day to avoid accumulating storage.

Public repository schedules can be disabled after 60 days without repository
activity. Re-enable the workflow in Actions if that occurs. Agency notices
that conflict with GTFS still require separate review; refresh validation
cannot establish that the agencies' schedules are correct.

## Calendar-independent checks

Tests against downloaded schedules must select dates from the input calendars using
`supporting_files/tests/helpers/service_date.js` and the production `serviceApplies`
function. Never use a literal date or today's date for these integration checks:
a rolling feed may no longer include a historical date, or may start tomorrow.
Select dates for the specific routes/operators being checked. Comparisons and
transfers must have overlapping service. Missing required routes or overlapping
coverage must fail, rather than skip assertions. Fixed dates remain appropriate
for self-contained fixtures testing things like daylight saving or realtime matching.
`service_date.test.js` checks rolling calendars decades ahead, calendar gaps,
exclusions, leap days, and failures for missing/nonoverlapping service.

Date selection establishes routing correctness for the input dataset; it does not
establish freshness. `validate_refresh.py` independently rejects failed imports,
empty products, and products/required lines without current or future service.

## Long-term unattended operation

GitHub's native schedule alone cannot guarantee indefinite operation: public
repository schedules are disabled after 60 days without repository activity, and
scheduled jobs may be delayed. Do not rely on no-op commits to keep it alive.
For operation without site edits, use an external daily scheduler to dispatch the
existing `workflow_dispatch` workflow, with a narrowly scoped Actions credential
stored in that scheduler's secret store. Monitor successful publication separately
from workflow starts so a stopped scheduler, failed build, or failed deployment is
visible. Alert only when a publication deadline is missed or action is required.

A full unattended setup should also retry transient feed/network failures with
bounded backoff, preserve the last successfully validated deployment during
outages, and monitor remaining service coverage. Never bypass failed validation
or label an old feed as freshly retrieved to make a daily run appear successful.
External agency format changes or discontinuation of a supported route can still
require maintenance; automation cannot establish that an agency's data is correct.
