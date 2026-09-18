import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = os.environ["FLH_PUBLISHING_SHEET_ID"]
ARTICLE_TYPE = "Mini"

raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
if not raw:
    raise SystemExit("BLOCKED: Google service-account secret is missing.")

creds = service_account.Credentials.from_service_account_info(
    json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
sheets = build("sheets", "v4", credentials=creds)
values = sheets.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range="Untitled!A:Z"
).execute().get("values", [])
if not values:
    raise SystemExit("BLOCKED: Publishing Control sheet is empty.")

headers = values[0]
for raw_row in values[1:]:
    row = dict(zip(headers, raw_row + [""] * (len(headers) - len(raw_row))))
    if row.get("Type", "").strip().casefold() != ARTICLE_TYPE.casefold():
        continue
    if row.get("Status", "").strip().casefold() != "ready to publish":
        continue
    if row.get("Illustration Status", "").strip().casefold() != "complete":
        continue
    if row.get("IP Gate Passed", "").strip().casefold() != "yes":
        continue
    if not row.get("Drive File ID", "").strip():
        continue
    if row.get("Actual Publication Date", "").strip() or row.get("Live URL", "").strip():
        continue
    asset_id = row.get("FLH Asset ID", "").strip()
    if asset_id:
        print(asset_id)
