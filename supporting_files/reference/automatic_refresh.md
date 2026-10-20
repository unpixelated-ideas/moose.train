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
