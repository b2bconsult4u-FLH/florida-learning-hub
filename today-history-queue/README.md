# Today in Florida History Queue

Only entries marked `Approved for Publication` and due on the current `America/New_York` date are eligible. Future articles remain staged. Publication copies the dated article to a root-level live page and updates the homepage, monthly archive and sitemap. Retries preserve existing live articles and do not duplicate archive links.

## Unattended publication and recovery

GitHub Actions attempts publication at 3:17, 4:23, 5:41 and 6:17 a.m. Eastern. Its scheduler is best-effort and recent runs arrived hours late. Successful late no-op runs are not evidence of on-time publication.

The independent Work task `Publish and Verify FLH` runs at 8:15 a.m. Eastern. It replaces the former inspect-only task, retaining its identity. It can publish the already-approved current-date article using connected GitHub tools and the repository publishing script when source publication is incomplete. It commits only publication files atomically, never force-pushes, preserves past content, and verifies the exact Cloudflare deployment and live content when accessible. It reports queue/access/source/deployment failures and remains enabled. This combines recovery and verification in one task within the account's five-active-task limit. Other scheduled tasks are unchanged.

Missing GitHub scheduled events alone do not constitute a publication failure if independent recovery succeeded. The task distinguishes source preparation, a commit, successful Cloudflare deployment, and successful live-content verification.

Each GitHub run tests safeguards, commits publication and waits up to ten minutes for live verification. Missing approved entries now fail explicitly instead of silently succeeding. Queue changes trigger current-date validation; they do not publish upcoming dates early. Manual dispatch remains available.

## October 4 investigation

The approved Sputnik article existed but the source still featured October 3. No October 4 publishing run appeared before manual recovery. The October 3 first scheduled run began at 12:34 UTC (8:34 a.m. Eastern), made no commit because recovery had already published the article, and passed all live checks. The workflow is on main with a supported timezone setting and has recent successful scheduled runs; this is not a missing schedule or 60-day inactivity issue.

GitHub documents that scheduled events may be delayed or dropped. Internal scheduler reasons are not exposed in repository logs. The independent recovery path removes reliance on that scheduler; tomorrow's unattended run is still needed to establish timed delivery.

## Prepared week

October 5–11, 2026: Madison Starke Perry; Florida's 1939 Thanksgiving dispute; British East and West Florida; Mary Lee Graham; Santa Rosa Island; Hurricane Michael; Key West's 1846 hurricane. Source links are included in every staged HTML article. October 12 requires a new approved queue entry.
