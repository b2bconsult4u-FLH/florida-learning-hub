#!/usr/bin/env python3
"""Weekly FLH website-update digest. Dry-run by default; no subscriber data stored."""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://floridalearninghub.org"
API = "https://api.brevo.com/v3"
LIST_ID = int(os.getenv("BREVO_LIST_ID", "4"))
SENDER = {"name": "Florida Learning Hub", "email": "updates@floridalearninghub.org"}
LIMIT = 300
EXCLUDE = {"index.html", "today-in-florida-history.html", "privacy-and-your-data.html"}
END = dt.datetime.now(dt.timezone.utc)
# The preceding Monday through Saturday, in America/New_York, is determined by workflow.
WEEK_END = dt.date.fromisoformat(os.environ["FLH_WEEK_END"])
WEEK_START = WEEK_END - dt.timedelta(days=6)
ISSUE = f"FLH Weekly Website Updates — {WEEK_END.isoformat()}"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def additions():
    # Use the first introduction of each page, not revisions or scheduled article dates.
    lines = git("log", "--diff-filter=A", "--name-only", "--pretty=format:%aI", "--", "*.html").splitlines()
    date = None
    found = {}
    for line in lines:
        if re.match(r"^\d{4}-\d\d-\d\dT", line):
            # The action passes Eastern boundaries; timezone conversion below handles DST.
            date = dt.datetime.fromisoformat(line).astimezone(
                __import__("zoneinfo").ZoneInfo("America/New_York")
            ).date()
        elif line.endswith(".html") and date and WEEK_START <= date <= WEEK_END:
            path = Path(line)
            if len(path.parts) == 1 and path.name not in EXCLUDE and path.name not in found:
                found[path.name] = date
    return found


def metadata(filename):
    text = (ROOT / filename).read_text(encoding="utf-8")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    description = re.search(r"""<meta\s+name=["']description["']\s+content=["'](.*?)["']""", text, re.I | re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else filename[:-5].replace("-", " ").title()
    summary = html.unescape(description.group(1)).strip() if description else ""
    return title[:140], summary[:220]


def api(method, endpoint, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + endpoint, data=data, method=method, headers={
        "api-key": os.environ["BREVO_API_KEY"], "accept": "application/json",
        "content-type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def main():
    pages = []
    for filename, published in sorted(additions().items(), key=lambda x: (x[1], x[0]), reverse=True):
        if not (ROOT / filename).is_file():
            print(f"Page missing from checkout: {filename}", file=sys.stderr)
            continue
        title, summary = metadata(filename)
        # Confirm pages are live before notifying readers.
        url = SITE + "/" + urllib.parse.quote(filename)
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "FLH-Weekly-Digest/1.0"})
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status != 200:
                    continue
        except (urllib.error.URLError, TimeoutError):
            print(f"Not verified live: {url}", file=sys.stderr)
            continue
        pages.append((title, summary, url))
    print(f"{ISSUE}: {len(pages)} new verified pages ({WEEK_START} to {WEEK_END})")
    if not pages:
        print("No new pages; skipping.")
        return
    items = "".join(
        f'<li style="margin:0 0 18px"><a href="{html.escape(url)}?utm_source=brevo&amp;utm_medium=email&amp;utm_campaign=weekly_digest" style="color:#08777b;font-weight:bold">{html.escape(title)}</a>'
        + (f'<div>{html.escape(summary)}</div>' if summary else "") + "</li>"
        for title, summary, url in pages
    )
    body = f"""<!doctype html><html><body style="margin:0;background:#f1f5f4;font-family:Arial,sans-serif;color:#193b40">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table role="presentation" width="600" style="max-width:100%;background:#fff" cellpadding="24"><tr><td style="background:#0b777b;color:white;text-align:center"><h1>Florida Learning Hub</h1><p>What's new this week</p></td></tr>
<tr><td><p>Explore the newest additions to our website, published {WEEK_START:%B %d}–{WEEK_END:%B %d}.</p><ul>{items}</ul>
<p><a href="{SITE}/">Visit Florida Learning Hub</a></p></td></tr>
<tr><td style="background:#e7f2f0;text-align:center;font-size:12px;line-height:1.8">
<strong>Florida Learning Hub</strong><br>Educational Publishing &bull; Florida History &bull; Teaching Resources<br>
A publishing imprint supported by L&amp;W Elite Services LLC<br><br>
PO Box 691235<br>Vero Beach, FL 32969<br>United States<br>
<a href="{SITE}/">floridalearninghub.org</a><br><br>
You're receiving this email because you subscribed to Florida Learning Hub updates.<br>
<a href="{{{{ unsubscribe }}}}">Unsubscribe</a> &nbsp;|&nbsp;
<a href="{SITE}/privacy-and-your-data.html">Privacy &amp; Your Data</a>
</td></tr></table></td></tr></table></body></html>"""
    if os.getenv("FLH_NEWSLETTER_SEND") != "true":
        print("DRY RUN: no campaign created or sent.")
        print(json.dumps({"issue": ISSUE, "pages": [p[2] for p in pages]}, indent=2))
        return
    if not os.getenv("BREVO_API_KEY"):
        raise RuntimeError("BREVO_API_KEY secret is required")
    # Refuse to create a second campaign with the same issue name, even if an earlier run
    # created the campaign but failed before sending. Review in Brevo to recover.
    for offset in range(0, 500, 50):
        existing = api("GET", f"/emailCampaigns?limit=50&offset={offset}")
        campaigns = existing.get("campaigns", [])
        if any(c.get("name") == ISSUE for c in campaigns):
            print("Campaign already exists; refusing duplicate. Inspect in Brevo.")
            return
        if len(campaigns) < 50:
            break
    # Check subscriber count against daily quota; never send to a partial list.
    contacts = api("GET", f"/contacts/lists/{LIST_ID}/contacts?limit=1&offset=0")
    count = contacts.get("count")
    if not isinstance(count, int):
        raise RuntimeError("Unable to verify list size; refusing to send")
    if count > LIMIT:
        raise RuntimeError(f"{count} contacts exceeds configured daily allowance {LIMIT}; no send")
    payload = {
        "name": ISSUE,
        "subject": f"Florida Learning Hub | What's New This Week ({WEEK_END:%b %d})",
        "sender": SENDER,
        "replyTo": SENDER["email"],
        "recipients": {"listIds": [LIST_ID]},
        "htmlContent": body,
        "previewText": "New Florida history stories and educational resources from the past week.",
    }
    created = api("POST", "/emailCampaigns", payload)
    campaign_id = created["id"]
    print(f"Created Brevo campaign {campaign_id}")
    api("POST", f"/emailCampaigns/{campaign_id}/sendNow", {})
    print(f"Sent campaign {campaign_id}")


if __name__ == "__main__":
    main()
