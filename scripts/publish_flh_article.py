import io
import json
import os
import re
import sys
import zipfile
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SHEET_ID = os.environ["FLH_PUBLISHING_SHEET_ID"]
ASSET_ID = os.environ["FLH_ASSET_ID"].strip()
ARTICLE_TYPE = os.environ["FLH_ARTICLE_TYPE"].strip()
SHEET_RANGE = "Untitled!A:U"
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


def fail(message):
    print(f"BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(1)


def slugify(text):
    text = text.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def text_of(el):
    return "".join(t.text or "" for t in el.findall(".//w:t", NS)).strip()


def style_of(el):
    pstyle = el.find("./w:pPr/w:pStyle", NS)
    return pstyle.get(f"{{{NS['w']}}}val", "") if pstyle is not None else ""


def load_docx(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    root = ET.fromstring(z.read("word/document.xml"))
    relroot = ET.fromstring(z.read("word/_rels/document.xml.rels"))
    rels = {x.get("Id"): x.get("Target") for x in relroot}
    return z, root, rels


def extract_blocks(z, root, rels, asset_dir, slug):
    body = root.find("w:body", NS)
    blocks = []
    image_no = 0
    last_figure = None
    for el in list(body):
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            txt = text_of(el)
            blips = el.findall(".//a:blip", NS)
            if blips:
                for blip in blips:
                    rid = blip.get(f"{{{NS['r']}}}embed")
                    target = rels.get(rid, "")
                    if not target.startswith("media/"):
                        continue
                    image_no += 1
                    raw = z.read("word/" + target)
                    ext = Path(target).suffix.lower() or ".jpg"
                    name = f"{slug}-{image_no}{ext}"
                    asset_dir.mkdir(parents=True, exist_ok=True)
                    (asset_dir / name).write_bytes(raw)
                    alt_el = el.find(".//wp:docPr", NS)
                    alt = ""
                    if alt_el is not None:
                        alt = alt_el.get("descr") or alt_el.get("title") or ""
                    figure = {"kind": "figure", "src": f"assets/articles/{name}", "alt": alt, "caption": ""}
                    blocks.append(figure)
                    last_figure = figure
                if txt:
                    blocks.append({"kind": "p", "text": txt})
                continue
            if not txt:
                continue
            style = style_of(el).lower()
            # Captions immediately following an embedded image stay attached to that image.
            if last_figure is not None and ("caption" in style or txt.lower().startswith(("image:", "photo:", "map:"))):
                last_figure["caption"] = txt
                last_figure = None
            elif "title" in style:
                blocks.append({"kind": "title", "text": txt})
                last_figure = None
            elif "subtitle" in style:
                blocks.append({"kind": "subtitle", "text": txt})
                last_figure = None
            elif "heading 1" in style or style in ("heading1", "heading 2", "heading2"):
                blocks.append({"kind": "h2", "text": txt})
                last_figure = None
            elif "heading 3" in style or style == "heading3":
                blocks.append({"kind": "h3", "text": txt})
                last_figure = None
            elif "list" in style:
                blocks.append({"kind": "li", "text": txt})
                last_figure = None
            else:
                blocks.append({"kind": "p", "text": txt})
                last_figure = None
        elif tag == "tbl":
            rows = []
            for tr in el.findall("./w:tr", NS):
                cells = [text_of(tc) for tc in tr.findall("./w:tc", NS)]
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append({"kind": "table", "rows": rows})
            last_figure = None
    return blocks


def render_blocks(blocks, sheet_title, asset_id, article_type, pillar):
    # Use the tracker title as canonical H1; suppress duplicate document title lines.
    title_seen = False
    html = []
    in_list = False
    for b in blocks:
        k = b["kind"]
        if k != "li" and in_list:
            html.append("</ul>")
            in_list = False
        if k == "title":
            if not title_seen:
                title_seen = True
            continue
        if k == "subtitle":
            html.append(f'<p class="subtitle">{escape(b["text"])}</p>')
        elif k == "h2":
            html.append(f'<h2>{escape(b["text"])}</h2>')
        elif k == "h3":
            html.append(f'<h3>{escape(b["text"])}</h3>')
        elif k == "p":
            # Skip common production labels already represented by page metadata.
            if b["text"].strip() in (sheet_title, asset_id):
                continue
            html.append(f'<p>{escape(b["text"])}</p>')
        elif k == "li":
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f'<li>{escape(b["text"])}</li>')
        elif k == "figure":
            alt = escape(b["alt"] or sheet_title)
            cap = escape(b["caption"])
            figcap = f'<figcaption>{cap}</figcaption>' if cap else ""
            html.append(f'<figure style="margin:1.5rem 0 2rem;text-align:center;"><img src="{escape(b["src"])}" alt="{alt}" style="width:100%;height:auto;display:block;border-radius:4px;">{figcap}</figure>')
        elif k == "table":
            trs = []
            for row in b["rows"]:
                cells = "".join(f"<td>{escape(c)}</td>" for c in row)
                trs.append(f"<tr>{cells}</tr>")
            html.append('<table class="quick-facts">' + "".join(trs) + "</table>")
    if in_list:
        html.append("</ul>")
    return "".join(html)


def main():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        fail("GitHub secret FLH_GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        fail("FLH_GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON.")
    creds = service_account.Credentials.from_service_account_info(info, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ])
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
    for field, expected in {"Status":"Ready to Publish", "Illustration Status":"Complete", "IP Gate Passed":"Yes"}.items():
        if row.get(field, "").strip().casefold() != expected.casefold():
            fail(f"{field} must be '{expected}', found '{row.get(field, '')}'.")
    file_id = row.get("Drive File ID", "").strip()
    if not file_id:
        fail("Drive File ID is blank.")
    meta = drive.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    if meta.get("mimeType") != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        fail(f"Approved source must be a DOCX; found {meta.get('mimeType')}.")
    req = drive.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    dl = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    data = fh.getvalue()
    z, root, rels = load_docx(data)
    title = row.get("Title", "").strip() or ASSET_ID
    slug = row.get("Slug", "").strip() or slugify(title)
    # Full and Mini must never collide. Full gets the canonical title slug; Mini is explicit.
    if ARTICLE_TYPE.casefold() == "mini":
        slug += "-mini"
    out = Path(f"{slug}.html")
    if out.exists():
        fail(f"Destination {out} already exists; automatic overwrite is disabled.")
    blocks = extract_blocks(z, root, rels, Path("assets/articles"), slug)
    figures = [b for b in blocks if b["kind"] == "figure"]
    if not figures:
        fail("Approved DOCX contains no embedded image; publication stopped.")
    body = render_blocks(blocks, title, ASSET_ID, ARTICLE_TYPE, row.get("Pillar/Series", ""))
    description = f"{title} — a Florida Learning Hub article about Florida history."
    canonical = f"https://floridalearninghub.org/{slug}.html"
    og_image = "https://floridalearninghub.org/" + figures[0]["src"]
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{escape(description, quote=True)}"><title>{escape(title)} | Florida Learning Hub</title><link rel="stylesheet" href="style.css?v=20260913-7"><link rel="canonical" href="{canonical}"><meta name="author" content="Wm. E. McMullen II"><meta property="og:locale" content="en_US"><meta property="og:type" content="article"><meta property="og:site_name" content="Florida Learning Hub"><meta property="og:title" content="{escape(title, quote=True)} | Florida Learning Hub"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{og_image}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title, quote=True)} | Florida Learning Hub"><meta name="twitter:description" content="{escape(description, quote=True)}"><meta name="twitter:image" content="{og_image}"></head><body><div class="site"><header class="header"><a href="index.html"><img src="assets/flh-header.png" alt="Florida Learning Hub"></a></header><button class="nav-toggle" type="button" aria-expanded="false" aria-controls="primary-nav"><span aria-hidden="true">☰</span><span>Menu</span></button><nav class="nav" id="primary-nav" aria-label="Primary navigation"><a href="read-florida.html" aria-current="page">FLH Articles</a><a href="discover-pioneer-florida.html">Discover Pioneer Florida</a><a href="teach-pioneer-florida.html">Teach Pioneer Florida</a><a href="classroom-resources.html">Classroom Resources</a><a href="stories-and-books.html">Florida History Books</a><a href="today-in-florida-history.html">Today in Florida History</a></nav><main><section class="article"><div class="kicker">{escape(row.get("Pillar/Series", "Florida History"))} · {escape(ASSET_ID)}</div><h1>{escape(title)}</h1><p class="article-meta">Florida Learning Hub · {escape(ARTICLE_TYPE)}</p>{body}<p class="article-meta" style="text-align:center;margin-top:2rem;">Written by Wm. E. McMullen II<br>Published by Florida Learning Hub<br>FloridaLearningHub.org<br>© 2026 Florida Learning Hub. All rights reserved.</p></section></main><footer class="footer"><nav class="footer-links" aria-label="Footer navigation"><a href="index.html">Home</a><a href="read-florida.html">FLH Articles</a><a href="teach-pioneer-florida.html">Teachers</a><a href="classroom-resources.html">Classroom Resources</a><a href="stories-and-books.html">Florida History Books</a><a href="today-in-florida-history.html">Today in Florida History</a></nav><nav class="footer-links footer-trust-links" aria-label="About and editorial policies"><a href="about-flh.html">About FLH</a><a href="about-author.html">About the Author</a><a href="research-standards.html">Research Standards</a><a href="image-copyright-policy.html">Image &amp; Copyright</a><a href="corrections-policy.html">Corrections</a></nav><div>© 2026 Florida Learning Hub · Preserving Florida’s history, culture, agriculture, wildlife, and pioneer heritage.</div></footer></div><button class="back-to-top" type="button" aria-label="Back to top" title="Back to top"><span aria-hidden="true">↑</span> Top</button><script src="back-to-top.js?v=20260911-1" defer></script><script src="site-navigation.js?v=20260913-8" defer></script><script src="article-trust.js?v=20260913-2" defer></script></body></html>'''
    out.write_text(page, encoding="utf-8")
    print(f"READY: generated {out} with {len(figures)} embedded approved image(s).")


if __name__ == "__main__":
    main()
