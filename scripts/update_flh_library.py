import json
import os
import re
from html import escape
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = os.environ["FLH_PUBLISHING_SHEET_ID"]
ASSET_ID = os.environ["FLH_ASSET_ID"].strip()
ARTICLE_TYPE = os.environ.get("FLH_ARTICLE_TYPE", "Mini").strip()
LIBRARY = Path("read-florida.html")


def fail(message):
    raise SystemExit(f"BLOCKED: {message}")


def slugify(text):
    text = text.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def topic_for(pillar):
    p = pillar.casefold()
    if any(x in p for x in ("cattle", "ranch")):
        return "cattle-ranching"
    if any(x in p for x in ("spanish", "colonial")):
        return "spanish-colonial"
    if any(x in p for x in ("fort", "military")):
        return "military-forts"
    if "civil war" in p:
        return "civil-war"
    if any(x in p for x in ("road", "transport")):
        return "roads-transportation"
    if "family" in p:
        return "pioneer-families"
    if "modern" in p:
        return "modern-florida"
    return "pioneer-heritage"


def main():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        fail("Google service-account secret is missing.")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    sheets = build("sheets", "v4", credentials=creds)
    values = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="Untitled!A:Z"
    ).execute().get("values", [])
    if not values:
        fail("Publishing Control sheet is empty.")
    headers = values[0]
    rows = [dict(zip(headers, r + [""] * (len(headers) - len(r)))) for r in values[1:]]
    matches = [r for r in rows if r.get("FLH Asset ID", "").strip() == ASSET_ID and r.get("Type", "").strip() == ARTICLE_TYPE]
    if len(matches) != 1:
        fail(f"Expected one {ASSET_ID}/{ARTICLE_TYPE} row; found {len(matches)}.")
    row = matches[0]
    title = row.get("Title", "").strip() or ASSET_ID
    pillar = row.get("Pillar/Series", "").strip() or "Florida History"
    slug = row.get("Slug", "").strip() or slugify(title)
    if ARTICLE_TYPE.casefold() == "mini" and not slug.endswith("-mini"):
        slug += "-mini"
    href = f"{slug}.html"
    if not Path(href).exists():
        fail(f"Generated article {href} does not exist.")

    html = LIBRARY.read_text(encoding="utf-8")
    if f'href="{href}"' in html:
        print(f"LIBRARY: {ASSET_ID} already listed; no duplicate added.")
        return

    excerpt = row.get("Short Excerpt", "").strip() or row.get("Meta Description", "").strip()
    if not excerpt:
        excerpt = f"Explore the Florida history of {title}."
    topic = topic_for(pillar)
    card = (
        f'<div class="card article-library-card" data-article-card data-type="mini" data-topics="{topic}">'
        f'<div class="kicker">{escape(ASSET_ID)} · {escape(pillar)}</div>'
        f'<h2>{escape(title)}</h2><p>{escape(excerpt)}</p>'
        f'<a class="btn" href="{escape(href)}">Read Mini</a></div>\n'
    )
    marker = '<section class="grid article-library-grid" data-library-grid="mini">\n'
    if marker not in html:
        fail("Mini library insertion point was not found in read-florida.html.")
    html = html.replace(marker, marker + card, 1)
    total = len(re.findall(r"data-article-card(?:\s|>)", html))
    html = re.sub(r">\d+ articles found<", f">{total} articles found<", html, count=1)
    LIBRARY.write_text(html, encoding="utf-8")
    print(f"LIBRARY: added {ASSET_ID} -> {href}; {total} total article cards.")


if __name__ == "__main__":
    main()
