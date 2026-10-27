# GitHub development workflow (FLH and FLTract)

Audience: Bill, or any AI session picking this up cold. Contains no secrets, only the names of things.
Status: PROPOSED. Written 2026-10-27 after a controlled access test. Nothing here changes an existing production workflow. `OPERATIONS.md` (Today in Florida History publication) is unchanged and still governs publication.

## Standing rules

1. Nothing merges to `main`, modifies production infrastructure, or triggers a production deployment without Bill's explicit approval in chat. Automatic Cloudflare Pages *preview* builds on development branches are expected and do not constitute authorized production deployment.
2. Every change starts on its own clearly named branch and ends as a **draft** pull request.
3. Never print, copy, or commit secrets. Workflows reference secret names only.
4. Inspect workflow triggers before the first push of any branch (see "Side effects" below).
5. Do not weaken branch protection, disable Actions, or widen the GitHub App's repository access as part of routine work.

## What was verified on 2026-10-27 (FLH)

| Capability | Result | Notes |
|---|---|---|
| Authenticated repo listing, push permission | Works | Both repos report push permission |
| Read repository contents | Works | |
| Create branch by `git push` | Works | |
| Commit and push | Works | |
| Open draft PR (REST `POST /pulls`) | Works | Test PR #9 |
| Read PR and changed files | Works | |
| Update PR by pushing another commit | Works | PR showed 2 commits |
| Close PR without merging (REST `PATCH /pulls/{n}`) | Works | |
| Delete a remote branch (`git push --delete` and REST `DELETE /git/refs`) | **Blocked** | HTTP 403: "Write access to this GitHub API path is not permitted through this proxy." This is an execution-environment policy, not GitHub branch protection (the branch was unprotected, the repo has no rulesets, the account has admin). |
| GraphQL | Blocked | Use REST |
| Cloudflare Pages preview | Builds on branch push and PR | Preview URL is posted as a PR comment and a check run named "Cloudflare Pages". Preview is not production. |

## The workflow

### 1. Review current state
- `git fetch origin main` and read the latest `main` before starting; `main` moves on its own (scheduled publication commits by github-actions).
- List open PRs and existing branches so work is not duplicated.
- Read the repo's own docs (`README.md`, `OPERATIONS.md`, `ARCHITECTURE.md` where present).

### 2. Create a dedicated branch
- Name: `<type>/<short-description>-<YYYY-MM-DD>` with type one of `feat`, `fix`, `docs`, `chore`, `test`.
- Branch from the current `main` commit.
- Disposable test branches start with `test/` and contain the word "disposable" in the commit message.

### 3. Edit and test locally
- Keep each PR to one purpose. Do not touch published HTML, queue files, or workflow files unless that is the purpose of the PR.
- Run the repository's own test command before pushing (FLH: `node --test ops/cloudflare/test/ops.test.mjs`; FLTract: `npm ci --ignore-scripts` then the tests named in `fltract-foundation-tests.yml`).

### 4. Run automated checks
- Push the branch; the PR-triggered checks run automatically where they exist.
- Read the results through the REST API (`commits/{sha}/check-runs`, `actions/runs?branch=`), not by assumption.

### 5. Open a draft PR
- Target `main`, `draft: true`, title states the purpose, body states what changed, what was tested, and what is not changed.
- Commit messages and PR body end with the standard Claude attribution lines.

### 6. Review build results and previews
- Wait for the Cloudflare Pages check run to finish, then open the preview URL from the PR comment and look at the changed pages.
- A green check is not proof of the intended result; verify the actual page or output.

### 7. Prepare for owner approval
- Post a short summary: what changed, links to PR and preview, test results, risks, and anything unverified.
- Mark ready for review only when Bill asks.

### 8. Merge only after explicit authorization
- Claude does not merge on its own. After Bill approves in chat, merge using the method he names (squash is the default suggestion), then verify `main` and the live site.
- When the repository setting "Automatically delete head branches" is enabled, merging a PR normally deletes its source branch automatically; **closing an unmerged PR does not**.

### 9. Clean up
- Close superseded PRs without merging.
- Branch deletion from Claude's environment is currently blocked (see table). For **closed and unmerged** PRs, the owner must delete the source branch using the GitHub Branches page. For **merged** PRs, the repository setting "Automatically delete head branches" can automate cleanup.

## Side effects to check before the first push

### FLH (`florida-learning-hub`)
- Workflows with push triggers (`update-sitemap.yml`, `publish-today-history.yml`) run only on pushes to `main`. A push to any other branch does not start them.
- Scheduled workflows (article publisher every 15 minutes, today-in-history, weekly newsletter) are independent of branches.
- Do not run `workflow_dispatch` workflows (publish, refresh library, newsletter, ops deploy) as part of testing. They publish, commit to `main`, send email, or deploy.
- Cloudflare Pages builds a preview for any branch or PR. Anything committed becomes visible at a public `pages.dev` preview URL, so never commit private material, even on a test branch.

### FLTract (`fltract`)
Read-only review on 2026-10-27. No branches, files, or PRs were created there.
- Default branch: `main`.
- `fltract-foundation-tests.yml` runs on pushes to `main` and one integration branch, and on PRs touching intake, admin, contact, property-records, or package files.
- `intake-live-acceptance.yml` runs on PRs that touch only its own script or workflow file, and uses preview D1 with no email binding.
- `public-release-preflight.yml` runs on PRs touching any `*.html`, `assets/**`, or its own files.
- **`intake-email-acceptance.yml` can send real owner and office emails.** It runs only on pushes to branch `fix/intake-validation-current-main-2026-10-17` that touch `scripts/intake-email-acceptance.mjs` AND carry one exact commit message. Never push to that branch, never touch that script, and never use that commit message.
- Treat FLTract as containing client data. Use synthetic data only; never read or copy client records into tests, logs, or PR text.

## Known restrictions and owner actions

| Restriction | Effect | Owner action |
|---|---|---|
| Branch deletion blocked in Claude's environment | Test and finished branches accumulate | For closed/unmerged PRs, delete from GitHub Branches page; for merged PRs, optionally enable auto-delete of head branches |
| FLTract not attached with write credentials | Claude cannot yet open FLTract PRs or read its protection rules and Actions through the authenticated API | Bill to approve attaching FLTract with push access when FLTract work begins |
| Cloudflare dashboard not yet authorized | Preview and deployment settings can be seen only through the PR check and comment | Next integration step |
