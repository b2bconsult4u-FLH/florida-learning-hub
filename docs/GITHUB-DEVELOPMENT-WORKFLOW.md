# GitHub development workflow (FLH and FLTract)

Audience: Bill and any AI session picking this up cold. Contains no secrets, only the names of things.
Status: PROPOSED for Bill's review. Written 2026-10-27 and revised 2026-10-28. This document does not itself change or enforce production workflows. `OPERATIONS.md` continues to govern Today in Florida History publication.

## Standing rules

1. No merge to `main`, production infrastructure change, new manual production run, or production deployment without Bill's explicit approval. Previously authorized recurring automation continues under its existing operating rules; this does not authorize new or changed automation. Automatic development-branch previews are expected, but are not production approval.
2. Each change starts on a dedicated, clearly named branch and is submitted as a draft PR. Mark it ready only when Bill asks.
3. Never print, copy, or commit secrets. Protect production secrets and client data. Use synthetic data in tests, logs, and PRs.
4. Inspect the current workflow files and their triggers, the branch version, and possible side effects before the first push. Do not assume this document's dated trigger summary remains current.
5. Do not weaken branch protection, disable Actions, or widen repository access as routine work.
6. These are operating rules, not proof of technical enforcement. On 2026-10-28 both repository ruleset listings were empty; branch-protection reads were denied to the reviewing integration. An owner must inspect protection and bypass settings separately to establish what GitHub enforces.

## Dated access observations

On 2026-10-27 Claude's controlled FLH test created and pushed a branch, opened and updated draft PR #9, read it, and closed it without merging. Its attempts to delete the unprotected test branch by Git and REST were blocked by its proxy with HTTP 403. GraphQL was also blocked in that environment; REST worked. These are observations about that session, not universal GitHub restrictions.

On 2026-10-28 the separate reviewing GitHub connection reported push permission for both repositories and could read their workflow files; this does not establish that Claude's session can write to FLTract or read protection settings. Confirm each acting session's actual access when needed; do not request another attachment solely on the basis of the old test. Prior Cloudflare access was read-only; verify the acting session's current access. Do not change production settings without approval.

## Development and review

1. Fetch and inspect current `main`, open PRs, branches, and relevant repository docs before starting. FLH `main` can move through scheduled publication.
2. Create a branch from current `main`, named `<type>/<short-description>-<YYYY-MM-DD>` using `feat`, `fix`, `docs`, `chore`, or `test`. Disposable test branches start with `test/` and use “disposable” in the commit message.
3. Keep the PR focused. Do not change published HTML, queues, or workflow files unless the task calls for them. Run appropriate local tests before pushing: FLH's ops test is `node --test ops/cloudflare/test/ops.test.mjs`; FLTract's foundation workflow specifies `npm ci --ignore-scripts` and its test commands. Check current files and run additional tests appropriate to the change.
4. Before pushing, inspect triggers and side effects. Push, open a draft PR targeting `main`, and inspect the actual checks and results. PR descriptions should state the change, tests, risks, and unverified items. Use attribution as required by the acting tool; Claude's attribution convention applies to Claude, not every agent.
5. Review the relevant Cloudflare build and the preview for the exact commit. Inspect the changed pages or output; a green build alone does not verify behavior. Preview URLs and access restrictions differ by project; never put private material in a branch or public preview.
6. Give Bill the PR and preview links, test results, risks, deployment implications, and unverified items. No merge or production deployment until Bill explicitly approves the particular action. After authorization, use the agreed merge method and verify the resulting commit and applicable live deployment.
7. Close superseded PRs without merging when appropriate. Claude's tested environment could not delete remote branches. An owner can delete closed/unmerged branches through GitHub; for merged branches, the repository's optional “Automatically delete head branches” setting can do so if enabled. Closing an unmerged PR does not trigger that cleanup. Do not assume the setting is enabled.

## Deployment paths and acceptance

- **FLH:** Cloudflare Pages production is connected to `main`; a merge can lead to a live deployment. Development branches produce previews. Review the exact preview and check the live site after an approved production change.
- **FLTract:** Git-connected Worker builds and previews exist, but the public `fltract.com` route has been served by the separately API-deployed `fltract-public-boundary`. Verify the current build, deployment target, bindings, and live route for each change. A merge or successful preview alone does not establish that the public site changed.
- For FLTract intake or private-admin changes, use an isolated preview database and synthetic data; restrict test email to authorized test destinations. Verify database and email bindings, authenticated access, and signed-in desktop and mobile behavior. Keep public submissions disabled until the relevant live checks and Bill's approval are complete. Report separately what is **built and tested**, **connected**, and **verified live**. Obtain explicit authorization before any real-email test or consequential communication.

## Side effects: snapshot reviewed 2026-10-28

Re-read the relevant workflow on the branch that would run before any push or manual action. Trigger conditions and scripts can change. Never run a workflow merely to test this document.

### FLH (`florida-learning-hub`)

- The current `update-sitemap.yml` and `publish-today-history.yml` push triggers are restricted to `main` and their specified paths. The sitemap workflow can commit and notify IndexNow; the history workflow can publish and commit.
- The article publisher, Today in Florida History, and weekly newsletter have schedules independent of development branch pushes. Existing recurring automation remains governed by its established approvals and operating instructions.
- Do not dispatch publication, library refresh, newsletter, or ops deployment workflows as routine testing. Depending on the workflow they can publish, commit, send email, or deploy. The newsletter workflow can optionally send; verify its actual send configuration separately and do not assume it is enabled or disabled.
- FLH branch previews may be publicly accessible at `pages.dev`; never commit private material.

### FLTract (`fltract`)

- `fltract-foundation-tests.yml` runs on pushes to `main` and a named integration branch, on PRs matching its listed paths, and by manual dispatch.
- `intake-live-acceptance.yml` runs on PRs changing either or both of its listed script and workflow paths, even if other files also change; it also has a manual trigger. The current job uses preview D1 with no email binding.
- `public-release-preflight.yml` runs on PRs matching its HTML, assets, or listed script/workflow paths; it also has a restricted-branch push trigger and manual dispatch. Its production preflight makes a live HTTP check.
- **`intake-email-acceptance.yml` can send real owner and office emails.** In the reviewed `main` version, its push trigger specifies branch `fix/intake-validation-current-main-2026-10-17` and a change to `scripts/intake-email-acceptance.mjs`; its job additionally requires the exact head-commit message `Run controlled PR24 live email acceptance once`. These are current conditions, not a security guarantee: a branch's workflow or script can differ or change. During ordinary work do not push to that branch, touch that script, or use that message. Any real-email test requires Bill's explicit authorization.
