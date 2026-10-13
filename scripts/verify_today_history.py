#!/usr/bin/env python3
"""Wait for Cloudflare and fail visibly if today's publication is incomplete."""
import json
import os
import time
import urllib.request
from html import unescape
from datetime import datetime
from zoneinfo import ZoneInfo
from publish_today_history import ROOT, due_item

def checks(item):
    origin = 'https://floridalearninghub.org'
    return [
        ('article', origin + '/' + item['live_file'], ['<h1>' + item['title'] + '</h1>'] + [needle for image in item.get('images', []) for needle in ['src="' + image['src'] + '"', image['credit'], image['source_url']]]),
        ('homepage', origin + '/', ['Today in Florida History · ' + item['display_date'], 'href="' + item['live_file'] + '"']),
        ('archive', origin + '/today-in-florida-history.html', ['Featured Entry — ' + item['display_date'], 'href="' + item['live_file'] + '"']),
        ('sitemap', origin + '/sitemap.xml', [origin + '/' + item['live_file']]),
    ]

def verify(item, fetch):
    failures = []
    for name, url, needles in checks(item):
        try:
            body = unescape(fetch(url))
            if not all(n in body for n in needles):
                failures.append(name + ': expected publication content missing')
        except Exception as exc:
            failures.append(name + ': ' + str(exc))
    return failures

def fetch(url):
    req = urllib.request.Request(url + '?flh_verify=' + str(time.time_ns()), headers={'Cache-Control': 'no-cache', 'User-Agent': 'FLH-Publication-Verification/1.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode('utf-8')

def verify_image_files(item):
    failures = []
    for image in item.get('images', []):
        url = image['src'] if image['src'].startswith('https://') else 'https://floridalearninghub.org/' + image['src']
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'FLH-Publication-Verification/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                head = response.read(16)
                valid = head.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'GIF87a', b'GIF89a')) or (head[:4] == b'RIFF' and head[8:12] == b'WEBP')
                if not valid:
                    raise ValueError('response is not a supported image file')
        except Exception as exc:
            failures.append('image ' + image['src'] + ': ' + str(exc))
    return failures


def main():
    today = os.getenv('FLH_TODAY') or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    item = due_item(json.loads((ROOT / 'today-history-queue/manifest.json').read_text()), today)
    if not item:
        print(f'No approved entry due {today}; verification skipped.')
        return
    deadline = time.monotonic() + int(os.getenv('FLH_VERIFY_SECONDS', '600'))
    while True:
        failures = verify(item, fetch) + verify_image_files(item)
        if not failures:
            print(f'Verified live article, homepage, archive and sitemap for {today}.')
            return
        print('; '.join(failures), flush=True)
        if time.monotonic() >= deadline:
            raise SystemExit('Live publication verification failed: ' + '; '.join(failures))
        time.sleep(20)

if __name__ == '__main__':
    main()
