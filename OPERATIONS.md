# OPERATIONS — Today in Florida History publication

Audience: Bill, or any AI session picking this up cold. Contains no secrets, only the names of secrets.
Goal: the correct article is live every morning with nobody starting anything.

## Proposed deployment paths (not yet deployed)

| Path | Clock | What it does | Failure domain |
|---|---|---|---|
| 1. `flh-publish-clock` Worker (PRIMARY) | Cloudflare Cron, every 10 min, 07:00–13:59 UTC | From 4:00 a.m. Eastern: checks the live site; if today's approved entry is not live, dispatches the GitHub workflow. Stops once verified. | Cloudflare |
| 2. GitHub workflow `publish-today-history.yml` | Dispatch from path 1 or 3; also cron 3:17/4:23/5:41/6:17 ET (fallback) and push triggers | Tests, publishes (idempotent), commits, verifies the live article, homepage, archive and sitemap for up to 10 minutes | GitHub |
| 3. `flh-publish-watchdog` Worker | Cloudflare Cron, 7:05 and 7:35 a.m. Eastern | Checks the live site and whether the clock is still ticking. Dispatches one recovery run. Alerts (ntfy) only on a problem. | Cloudflare, separate script and secrets |
| 4. Healthchecks.io dead-man's switch | Expects a ping from each Worker | Emails you if a Worker **stops pinging**. This is the only part that notices a Worker that is not running at all. | Third party |

Why the heartbeat is external: a record written by the thing that stopped cannot report that it stopped. The Workers' own records are for measuring reliability; Healthchecks.io is what detects silence. The watchdog also checks the clock's last tick, and Healthchecks watches the watchdog.

Known property: a push that touches `today-history-queue/*.html` or the publish scripts also starts the workflow. That is how Oct 9 published at 5:48 a.m., not the schedule. Do not count a push-triggered run as proof that the schedule works.

## Daily timeline (Eastern)

- 4:00 first dispatch attempt if not live; repeats every 10 min while nothing is in flight.
- 7:05 watchdog check. 7:35 second check (escalates).
- Expected normal result: live by about 4:10 a.m.

## One-time setup (requires authorized service access)

1. **GitHub token.** Fine-grained personal access token, this repo only: Actions = Read and write, Contents = Read. Set a calendar reminder before it expires.
2. **KV.** `npx wrangler kv namespace create FLH_STATE`; paste the id into both `wrangler.toml` files.
3. **Healthchecks.io** (free). Create two checks:
   - `FLH clock`: cron schedule `*/10 7-13 * * *`, timezone UTC, grace 25 minutes.
   - `FLH watchdog`: cron schedule `5,35 11,12 * * *`, timezone UTC, grace 3 hours.
   Add your email as the integration. Copy each ping URL.
4. **ntfy.** Pick a long random topic name; subscribe to it in the ntfy phone app.
5. **Deploy**, from `ops/cloudflare/clock` and `ops/cloudflare/watchdog`:
   ```
   npx wrangler secret put GITHUB_TOKEN     # both
   npx wrangler secret put HC_CLOCK_URL     # clock
   npx wrangler secret put HC_WATCHDOG_URL  # watchdog
   npx wrangler secret put NTFY_TOPIC       # watchdog
   npx wrangler secret put STATUS_TOKEN     # watchdog (any long random string)
   npx wrangler deploy
   ```
6. Test before trusting: `cd ops/cloudflare && npm test` (17 tests, no network).

## Triage: find which stage failed (do this before changing anything)

1. Healthchecks.io dashboard: is the clock or watchdog **late**? If yes, the Worker is not running; check Cloudflare dashboard, Workers, Cron Triggers, and the token/secret.
2. Status report: `curl -H "Authorization: Bearer $STATUS_TOKEN" https://flh-publish-watchdog.<account>.workers.dev/status` shows each day's `first_missing_at`, `first_dispatch_at`, `live_at`, `attempts`, and a count of days live before 7:00.
3. GitHub, Actions, "Publish Today in Florida History": open the latest run and read the **Publication trigger record** in the summary (event, actor, start time).

| Symptom | Likely stage | Action |
|---|---|---|
| Clock record says `error` with `dispatch failed: HTTP 401/403` | GitHub token expired or lacks Actions write | Replace the token secret on both Workers |
| `no-approved-entry` | Queue | Add/approve the entry in `today-history-queue/manifest.json` |
| `dispatched` every 10 min, never live | Workflow runs but publish or deploy fails | Open the run; failed step names the stage. Check Cloudflare Pages build for the same time |
| Run green but site not updated | Cloudflare Pages deploy | Pages dashboard build log |
| No dispatch and no tick records | Cloudflare cron not running | Dashboard, Cron Triggers; redeploy |

## Manual recovery (always safe; the publish script is idempotent)

- GitHub, Actions, "Publish Today in Florida History", **Run workflow**. Leave the date empty for today.
- For a specific date: enter `YYYY-MM-DD` in `publish_date`.
- From a shell with a token: `gh workflow run publish-today-history.yml --ref main`
- Never edit the live HTML by hand to "fix" a day; fix the queue entry and re-run.

## Status and acceptance

Do not call this repaired until all of these are true, from the status report:
- 14 consecutive mornings with `live_at` earlier than 7:00 a.m. Eastern, **with no manual start and no push-triggered run**.
- Failure drill passed once: pause the clock Worker's cron, confirm Healthchecks emails you within its grace and the watchdog alerts at 7:05; then restore it.
- Dispatch-failure drill: set a bad `GITHUB_TOKEN` on a test day and confirm `/fail` ping and alert.

## Other schedulers

The enabled ChatGPT Work task "Publish and Verify FLH" runs at 8:15 a.m. Eastern. Preserve it as an additional backstop; do not create a duplicate.

## Current deployment state and evidence limits

These Workers are source code pending deployment. KV namespace IDs and runtime secrets must be configured. Clock and watchdog share Cloudflare and KV; Healthchecks provides the external silence detector. The 8:15 Eastern ChatGPT Work task "Publish and Verify FLH" was located and is enabled; preserve it as a backstop.

The status report counts observations, not proven publication times. It does not certify the 14-day acceptance test. Correlate article/date, GitHub run IDs, caller labels, actors and event types before counting an unattended day. Caller labels are descriptive, not authentication. Missing approved content is unhealthy. The 7:05 check initiates recovery; unresolved publication alerts escalate at 7:35. Clock failures alert immediately. All requests have 15-second timeouts.

## Deployment through GitHub Actions

The manual workflow `Deploy FLH publication clock and watchdog` performs a credential preflight, runs tests, creates or reuses `flh-publication-state` KV, deploys each Worker without cron, installs its secrets, then enables and reads back its schedule. It does not run until explicitly started.

Required repository Actions secrets: `CLOUDFLARE_API_TOKEN` (scoped to FLH account with Workers Scripts Edit and Workers KV Storage Edit), `CLOUDFLARE_ACCOUNT_ID`, `FLH_DISPATCH_TOKEN` (fine-grained GitHub token scoped to this repository, Actions write and Contents read), `HC_CLOCK_URL`, `HC_WATCHDOG_URL`, `NTFY_TOPIC`, and `STATUS_TOKEN`. Secrets must be entered through the provider's secure UI, never in source or chat. Missing secrets stop deployment before changes.
