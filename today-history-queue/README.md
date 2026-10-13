# Today in Florida History Queue

Only entries marked `Approved for Publication` and due on the current `America/New_York` date are eligible. Future articles remain staged. Publication copies the dated article to a root-level live page and updates the homepage, monthly archive and sitemap. Retries preserve existing live articles and do not duplicate archive links.

## Unattended publication and recovery

GitHub Actions attempts publication at 3:17, 4:23, 5:41 and 6:17 a.m. Eastern. Its scheduler is best-effort and recent runs arrived hours late. Successful late no-op runs are not evidence of on-time publication.

The deployed Cloudflare Worker `flh-publish-clock` checks the approved current-date queue and live article, homepage, archive, and sitemap. Its UTC cron runs every ten minutes from 07:00 through 13:59; the code acts from 4 a.m. Eastern and handles daylight saving time. If publication is incomplete and no fresh GitHub run is underway, it dispatches `publish-today-history.yml` with `trigger_source=cloudflare-clock`. GitHub publishes and verifies the site. The separate `flh-publish-watchdog` checks and attempts recovery during the 7 a.m. Eastern hour. Current deployment has GITHUB_TOKEN and KV bindings; external notification secrets are not configured, so external alerts must not be claimed.

Work's `Publish and Verify FLH` automation was paused on October 13, 2026. It must not publish daily or conceal independent scheduler failures. The clock's KV record shows an October 13 dispatch at 12:00 UTC (8:00 a.m. EDT); GitHub run 38394119855's log records `SOURCE: cloudflare-clock`, and KV records verified live content at 8:10 a.m. This proves independent publication, but does not prove delivery by 6:30 a.m. Future runs must be assessed using their actual trigger, dispatch, and live-verification times. Workflow run titles now expose the caller label.

Each GitHub run tests safeguards, commits publication and waits up to ten minutes for live verification. Missing approved entries now fail explicitly instead of silently succeeding. Queue changes trigger current-date validation; they do not publish upcoming dates early. Manual dispatch remains available.

## October 4 investigation

The approved Sputnik article existed but the source still featured October 3. No October 4 publishing run appeared before manual recovery. The October 3 first scheduled run began at 12:34 UTC (8:34 a.m. Eastern), made no commit because recovery had already published the article, and passed all live checks. The workflow is on main with a supported timezone setting and has recent successful scheduled runs; this is not a missing schedule or 60-day inactivity issue.

GitHub documents that scheduled events may be delayed or dropped. Internal scheduler reasons are not exposed in repository logs. The independent recovery path removes reliance on that scheduler; tomorrow's unattended run is still needed to establish timed delivery.

## Prepared week

October 5–11, 2026: Madison Starke Perry; Florida's 1939 Thanksgiving dispute; British East and West Florida; Mary Lee Graham; Santa Rosa Island; Hurricane Michael; Key West's 1846 hurricane. Source links are included in every staged HTML article. October 12 requires a new approved queue entry.

## Images required in articles

Every associated publication image must be embedded in the article with descriptive alt text, an accurate caption, archive/creator credit, and an optional link to the original record. Readers must not need to leave FLH to see the image. Prefer a verified local asset under `assets/`; do not ship broken remote images or claim a different photograph shows the same scene. Before approval, verify that each embedded image renders. Keep the staged and live correction synchronized. Generated illustrations must be labeled as illustrations, never as archival photographs.

Record associated images in each manifest entry's `images` list with `src`, `credit`, and `source_url`. The publisher requires an embedded image with alt text, source link and credit, and checks that local assets exist. Live verification checks those details and downloads each declared image to reject missing files or HTML error pages returned as images.
