import io
import json
import os
import re
import sys
from pathlib import Path

from docx import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SHEET_ID = os.environ["FLH_PUBLISHING_SHEET_ID"]
ASSET_ID = os.environ["FLH_ASSET_ID"].strip()
ARTICLE_TYPE = os.environ["FLH_ARTICLE_TYPE"].strip()
SHEET_RANGE = "Untitled!A:U"


def fail(message):
    print(f"BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(1)


def slugify(text):
    text = text.lower().replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def main():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        fail("GitHub secret FLH_GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"],
    )
    sheets = build("sheets", "v4", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    values = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute().get("values", [])
    if not values:
        fail("Publishing Control sheet is empty.")
    headers = values[0]
    rows = [dict(zip(headers, r + [""] * (len(headers) - len(r)))) for r in values[1:]]
    matches = [r for r in rows if r.get("FLH Asset ID", "").strip() == ASSET_ID and r.get("Type", "").strip() == ARTICLE_TYPE]
    if len(matches) != 1:
        fail(f"Expected exactly one {ASSET_ID} / {ARTICLE_TYPE} row; found {len(matches)}.")
    row = matches[0]

    required = {
        "Status": "Ready to Publish",
        "Illustration Status": "Complete",
        "IP Gate Passed": "Yes",
    }
    for field, expected in required.items():
        if row.get(field, "").strip().casefold() != expected.casefold():
            fail(f"{field} must be '{expected}', found '{row.get(field, '')}'.")

    file_id = row.get("Drive File ID", "").strip()
    if not file_id:
        fail("Drive File ID is blank.")

    meta = drive.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    if meta.get("mimeType") != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        fail(f"Approved source must be a DOCX; found {meta.get('mimeType')}.")

    request = drive.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    doc = Document(fh)

    # Guardrail: this first controlled publisher refuses documents without embedded images.
    if not doc.inline_shapes:
        fail("Approved DOCX contains no embedded image; publication stopped.")

    title = row.get("Title", "").strip() or ASSET_ID
    slug = row.get("Slug", "").strip() or slugify(title)
    out = Path(f"{slug}.html")
    if out.exists():
        fail(f"Destination {out} already exists; automatic overwrite is disabled.")

    paragraphs = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        paragraphs.append(f"<p>{esc(t)}</p>")

    # This is intentionally a guarded first-stage conversion. Embedded images are verified
    # above, but image extraction/placement is not guessed. A live page is not emitted until
    # the converter can preserve the approved document's image placement and captions.
    fail("Source and all three publication gates verified successfully. Image-preserving DOCX-to-FLH conversion is the next stage; no page was published.")


if __name__ == "__main__":
    main()
