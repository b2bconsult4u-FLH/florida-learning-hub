import json
import os
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = os.environ["FLH_PUBLISHING_SHEET_ID"]
ASSET_ID = os.environ["FLH_ASSET_ID"].strip()
ARTICLE_TYPE = os.environ.get("FLH_ARTICLE_TYPE", "Mini").strip()
COMMIT_SHA = os.environ["FLH_PUBLISH_COMMIT_SHA"].strip()


def fail(message):
    raise SystemExit(f"BLOCKED: {message}")


def main():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        fail("Google service-account secret is missing.")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    sheets = build("sheets", "v4", credentials=creds)
    values = sheets.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="Untitled!A:Z"
    ).execute().get("values", [])
    if not values:
        fail("Publishing Control sheet is empty.")
    headers = values[0]
    found = []
    for sheet_row, raw_row in enumerate(values[1:], start=2):
        row = dict(zip(headers, raw_row + [""] * (len(headers) - len(raw_row))))
        if row.get("FLH Asset ID", "").strip() == ASSET_ID and row.get("Type", "").strip() == ARTICLE_TYPE:
            found.append((sheet_row, row))
    if len(found) != 1:
        fail(f"Expected one {ASSET_ID}/{ARTICLE_TYPE} row; found {len(found)}.")
    sheet_row, row = found[0]
    slug = row.get("Slug", "").strip()
    if not slug:
        fail("Slug is blank during publication writeback.")
    if ARTICLE_TYPE.casefold() == "mini" and not slug.endswith("-mini"):
        slug += "-mini"
    live_url = f"https://floridalearninghub.org/{slug}.html"
    now = datetime.now(timezone.utc)
    publication_date = now.date().isoformat()
    last_run = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = [["Published", publication_date, live_url, COMMIT_SHA, last_run, "Success — article generated, library listing updated, and GitHub publication commit pushed."]]
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"Untitled!E{sheet_row}:J{sheet_row}",
        valueInputOption="RAW",
        body={"values": payload},
    ).execute()
    # E:J would overwrite unrelated production columns, so immediately restore those fields from the source row.
    restore = [[
        "Published",
        row.get("Priority", ""),
        row.get("Illustration Status", ""),
        row.get("IP Gate Passed", ""),
        row.get("Drive File ID", ""),
        row.get("Featured Image File ID", ""),
    ]]
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=f"Untitled!E{sheet_row}:J{sheet_row}", valueInputOption="RAW", body={"values": restore}
    ).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=f"Untitled!Q{sheet_row}:U{sheet_row}", valueInputOption="RAW",
        body={"values": [[publication_date, live_url, COMMIT_SHA, last_run, "Success — article generated, library listing updated, and GitHub publication commit pushed."]]}
    ).execute()
    print(f"WRITEBACK: {ASSET_ID} row {sheet_row} marked Published -> {live_url} @ {COMMIT_SHA[:7]}")


if __name__ == "__main__":
    main()
