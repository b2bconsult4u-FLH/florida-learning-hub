# Today in Florida History Queue

GitHub Actions attempts publication daily at 3:17, 4:23, 5:41 and 6:17 a.m. America/New_York, with daylight-saving adjustments. Only entries marked `Approved for Publication` and due on the Eastern date are eligible. Prepared HTML is copied into a live page, the homepage and archive are updated, and publication files are committed together. Repeated runs preserve the live article and do not duplicate archive entries.

Each run verifies the remote commit and waits up to ten minutes for the live article, homepage feature, archive and sitemap. Failed checks fail the workflow visibly. Manual dispatch remains available for controlled recovery. Changes to the publication workflow or scripts also trigger a validation run; this is a `push` run, not proof of a scheduled run.

The separate Work check at 6:30 a.m. only inspects and reports failures. It must never publish, commit, dispatch or repair articles. GitHub scheduled events remain best-effort; four attempts are recovery opportunities, not a guarantee. The decisive evidence is a successful run with event `schedule` and its publication commit.
