#!/usr/bin/env python3
"""Publish one approved Eastern-date entry; retries repair without duplicating."""
import json
import os
import re
from html import escape, unescape
from html.parser import HTMLParser
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

class ArticleImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            self.images.append(attrs)
        elif tag == 'a':
            self.links.append(attrs.get('href'))

class NarrativeWords(HTMLParser):
    """Count narrative paragraphs, excluding headings, citations and teaching aids."""
    def __init__(self):
        super().__init__()
        self.sections = 0
        self.excluded = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == 'section':
            if self.sections or dict(attrs).get('id') == 'historical-narrative':
                self.sections += 1
        if self.sections and tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'sup', 'figcaption', 'script', 'style'}:
            self.excluded.append(tag)
    def handle_endtag(self, tag):
        if self.excluded and tag == self.excluded[-1]:
            self.excluded.pop()
        if tag == 'section' and self.sections:
            self.sections -= 1
    def handle_data(self, data):
        if self.sections and not self.excluded:
            self.text.append(data)

def narrative_word_count(article):
    parser = NarrativeWords()
    parser.feed(article)
    return len(' '.join(parser.text).split())

def validate_editorial(item, article):
    requirements = item.get('editorial_requirements', {})
    minimum = requirements.get('minimum_narrative_words', 0)
    if minimum:
        count = narrative_word_count(article)
        if count < minimum:
            raise ValueError(f'Historical narrative has {count} words; minimum is {minimum}')
    if requirements.get('classroom_resources'):
        for marker in ('id="classroom-connection"', 'Reading Prompt', 'Glossary', 'Reading Check', 'Think and Discuss', 'Short Writing Prompt', 'Teacher Notes and Suggested Answers'):
            if marker not in article:
                raise ValueError('Classroom resource missing: ' + marker)

def validate_images(item, article):
    parser = ArticleImages()
    parser.feed(article)
    for image in item.get('images', []):
        matches = [x for x in parser.images if x.get('src') == image['src']]
        if not matches or not all(x.get('alt', '').strip() for x in matches):
            raise ValueError('Associated image must be embedded with alt text: ' + image['src'])
        if image['credit'] not in unescape(article) or image['source_url'] not in parser.links:
            raise ValueError('Associated image credit/source missing: ' + image['src'])
        if not image['src'].startswith(('https://', 'http://')):
            asset = (ROOT / image['src']).resolve()
            if not asset.is_relative_to(ROOT.resolve()) or not asset.is_file():
                raise ValueError('Associated local image missing: ' + image['src'])


def main():
    today = os.getenv('FLH_TODAY') or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    manifest = ROOT / 'today-history-queue/manifest.json'
    data = json.loads(manifest.read_text())
    item = due_item(data, today)
    if not item:
        raise ValueError(f'No approved entry due {today}; queue needs attention. No publication changes.')
    staged = ROOT / 'today-history-queue' / item['staged_file']
    live = ROOT / item['live_file']
    if not staged.is_file():
        raise ValueError(f'Approved staged article missing: {staged}')
    validate_editorial(item, staged.read_text())
    validate_images(item, staged.read_text())
    if live.exists():
        validate_images(item, live.read_text())
    archive_path, home_path = ROOT / 'today-in-florida-history.html', ROOT / 'index.html'
    archive, home = archive_path.read_text(), home_path.read_text()
    marker = '<section class="article">'
    if marker not in archive:
        raise ValueError('Archive section marker not found')
    entry = f'<h2>Featured Entry — {item["display_date"]}</h2><h2>{item["display_date"]} — {item["title"]}</h2><p>{item["summary"]}</p><p><a class="btn" href="{item["live_file"]}">Read {item["display_date"]}: {item["link_title"]}</a></p><hr>'
    link = f'href="{item["live_file"]}"'
    archive_links = archive.split('<!-- history-months:start -->', 1)[-1] if '<!-- history-months:start -->' in archive else archive
    if archive_links.count(link) > 1:
        raise ValueError('Duplicate archive links detected')
    if '<!-- history-feature:start -->' in archive:
        archive = re.sub(r'<!-- history-feature:start -->.*?<!-- history-feature:end -->', '<!-- history-feature:start -->' + entry.removesuffix('<hr>') + '<!-- history-feature:end -->', archive, count=1, flags=re.S)
        if link not in archive[archive.index('<!-- history-months:start -->'):]:
            month, day = item['display_date'].rsplit(' ', 1)
            row = f'<li data-day="{int(day)}"><a href="{item["live_file"]}"><strong>{item["display_date"]}</strong> — {escape(item["title"])}</a></li>'
            month_id = 'history-' + month.lower()
            pattern = rf'(<details class="history-month" id="{month_id}"[^>]*><summary>)(.*?)(</summary><ul class="history-date-list">)(.*?)(</ul></details>)'
            match = re.search(pattern, archive, re.S)
            if match:
                rows = re.findall(r'<li data-day="\d+">.*?</li>', match[4], re.S) + [row]
                rows.sort(key=lambda r: int(re.search(r'data-day="(\d+)"', r)[1]))
                block = match[1] + f'{month} — {len(rows)} stories' + match[3] + ''.join(rows) + match[5]
                archive = archive[:match.start()] + block + archive[match.end():]
            else:
                block = f'<details class="history-month" id="{month_id}" open><summary>{month} — 1 stories</summary><ul class="history-date-list">{row}</ul></details>'
                archive = archive.replace('<!-- history-months:start -->', '<!-- history-months:start -->' + block, 1)
    elif link not in archive:
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
