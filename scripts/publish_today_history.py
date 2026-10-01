#!/usr/bin/env python3
"""Publish one approved Eastern-date entry; retries repair without duplicating."""
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]

def due_item(data, today):
    date.fromisoformat(today)
    items = [x for x in data['entries'] if x['publish_date'] == today and x.get('status') == 'Approved for Publication']
    if len(items) > 1:
        raise ValueError(f'Multiple approved entries for {today}')
    return items[0] if items else None

def replace_panel(home, panel):
    start = home.find('<div class="panel"><div class="kicker">Today in Florida History')
    if start < 0:
        raise ValueError('Homepage history panel not found')
    depth = 0
    for match in re.finditer(r'</?div\b[^>]*>', home[start:]):
        depth += -1 if match.group().startswith('</') else 1
        if depth == 0:
            return home[:start] + panel + home[start + match.end():]
    raise ValueError('Homepage history panel is unbalanced')

def main():
    today = os.getenv('FLH_TODAY') or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    manifest = ROOT / 'today-history-queue/manifest.json'
    data = json.loads(manifest.read_text())
    item = due_item(data, today)
    if not item:
        print(f'No approved entry due {today}; no publication changes.')
        return
    staged = ROOT / 'today-history-queue' / item['staged_file']
    live = ROOT / item['live_file']
    if not staged.is_file():
        raise ValueError(f'Approved staged article missing: {staged}')
    archive_path, home_path = ROOT / 'today-in-florida-history.html', ROOT / 'index.html'
    archive, home = archive_path.read_text(), home_path.read_text()
    marker = '<section class="article">'
    if marker not in archive:
        raise ValueError('Archive section marker not found')
    entry = f'<h2>Featured Entry — {item["display_date"]}</h2><h2>{item["display_date"]} — {item["title"]}</h2><p>{item["summary"]}</p><p><a class="btn" href="{item["live_file"]}">Read {item["display_date"]}: {item["link_title"]}</a></p><hr>'
    link = f'href="{item["live_file"]}"'
    if archive.count(link) > 1:
        raise ValueError('Duplicate archive links detected')
    if link not in archive:
        archive = archive.replace(marker, marker + entry, 1)
    panel = f'<div class="panel"><div class="kicker">Today in Florida History · {item["display_date"]}</div><h2>{item["title"]}</h2><p>{item["summary"]}</p><p><a class="btn" href="{item["live_file"]}">Read: {item["link_title"]}</a></p></div>'
    home = replace_panel(home, panel)
    data['last_featured'] = item['display_date']
    # Validate all structure before writing. Existing live articles are preserved.
    files = {archive_path: archive, home_path: home, manifest: json.dumps(data, indent=2) + '\n'}
    if not live.exists():
        files[live] = staged.read_text()
    for path, text in files.items():
        if not path.exists() or path.read_text() != text:
            path.write_text(text)
    print(f'Publication ready: {item["live_file"]} ({today})')

if __name__ == '__main__':
    main()
