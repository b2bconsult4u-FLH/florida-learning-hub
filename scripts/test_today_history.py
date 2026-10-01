import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import publish_today_history as publish
import verify_today_history as verification

class PublicationTests(unittest.TestCase):
    def test_retries_and_next_day_preserve_structure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue = root / 'today-history-queue'
            queue.mkdir()
            entries = []
            for day in ('01', '02'):
                item = dict(publish_date='2026-10-' + day, display_date='October ' + str(int(day)), status='Approved for Publication', title='Story ' + day, summary='Summary', link_title='Story', staged_file=day + '.html', live_file='today-' + day + '.html')
                entries.append(item)
                (queue / item['staged_file']).write_text('approved ' + day)
            (queue / 'manifest.json').write_text(json.dumps({'entries': entries}))
            (root / 'index.html').write_text('<main><div class="panel"><div class="kicker">Today in Florida History · Yesterday</div><h2>Old</h2></div><section>Keep</section></main>')
            (root / 'today-in-florida-history.html').write_text('<section class="article"><p>Keep archive</p></section>')
            with patch.object(publish, 'ROOT', root), patch.dict(os.environ, FLH_TODAY='2026-10-01'):
                publish.main()
                before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                publish.main()
                self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})
            with patch.object(publish, 'ROOT', root), patch.dict(os.environ, FLH_TODAY='2026-10-02'):
                publish.main()
            home = (root / 'index.html').read_text()
            self.assertNotIn('Story 01', home)
            self.assertIn('Story 02', home)
            self.assertEqual(home.count('<div'), home.count('</div>'))
            self.assertIn('<section>Keep</section>', home)
            archive = (root / 'today-in-florida-history.html').read_text()
            self.assertEqual(archive.count('href="today-01.html"'), 1)
            self.assertEqual(archive.count('href="today-02.html"'), 1)

    def test_approval_and_date_gate(self):
        item = dict(publish_date='2026-10-02', status='Draft')
        self.assertIsNone(publish.due_item({'entries': [item]}, '2026-10-02'))
        item['status'] = 'Approved for Publication'
        self.assertIsNone(publish.due_item({'entries': [item]}, '2026-10-01'))
        with self.assertRaises(ValueError):
            publish.due_item({'entries': [item, item]}, '2026-10-02')

    def test_verifier_rejects_stale_or_failed_pages(self):
        item = dict(title='New', display_date='October 2', live_file='today-new.html')
        self.assertEqual(len(verification.verify(item, lambda url: 'stale')), 4)
        bodies = {url: '\n'.join(needles) for _, url, needles in verification.checks(item)}
        self.assertEqual(verification.verify(item, bodies.__getitem__), [])

if __name__ == '__main__':
    unittest.main()
