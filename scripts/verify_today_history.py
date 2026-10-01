#!/usr/bin/env python3
"""Wait for Cloudflare and fail visibly if today's publication is incomplete."""
import json
import os
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from publish_today_history import ROOT, due_item

def checks(item):
    origin = 'https://floridalearninghub.org'
    return [
        ('article', origin + '/' + item['live_file'], ['<h1>' + item['title'] + '</h1>']),
        ('homepage', origin + '/', ['Today in Florida History · ' + item['display_date'], 'href="' + item['live_file'] + '"']),
        ('archive', origin + '/today-in-florida-history.html', ['Featured Entry — ' + item['display_date'], 'href="' + item['live_file'] + '"']),
        ('sitemap', origin + '/sitemap.xml', [origin + '/' + item['live_file']]),
    ]

def verify(item, fetch):
    failures = []
    for name, url, needles in checks(item):
        try:
            body = fetch(url)
            if not all(n in body for n in needles):
                failures.append(name + ': expected publication content missing')
        except Exception as exc:
            failures.append(name + ': ' + str(exc))
    return failures

def fetch(url):
    req = urllib.request.Request(url + '?flh_verify=' + str(time.time_ns()), headers={'Cache-Control': 'no-cache', 'User-Agent': 'FLH-Publication-Verification/1.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode('utf-8')

def main():
    today = os.getenv('FLH_TODAY') or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    item = due_item(json.loads((ROOT / 'today-history-queue/manifest.json').read_text()), today)
    if not item:
        print(f'No approved entry due {today}; verification skipped.')
        return
    deadline = time.monotonic() + int(os.getenv('FLH_VERIFY_SECONDS', '600'))
    while True:
        failures = verify(item, fetch)
        if not failures:
            print(f'Verified live article, homepage, archive and sitemap for {today}.')
            return
        print('; '.join(failures), flush=True)
        if time.monotonic() >= deadline:
            raise SystemExit('Live publication verification failed: ' + '; '.join(failures))
        time.sleep(20)

if __name__ == '__main__':
    main()
