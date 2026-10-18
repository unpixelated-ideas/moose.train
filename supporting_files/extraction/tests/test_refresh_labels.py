import importlib.util
from pathlib import Path
import unittest
import csv
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('refresh_labels', ROOT / 'supporting_files/scripts/update_refresh_labels.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RefreshLabelTests(unittest.TestCase):
    def records(self):
        return [dict(feed_id=feed, success='true', imported_at='2026-10-18T00:30:00+00:00')
                for feed in ('mnr', 'hartford', 'sle', 'amtrak')]

    def test_eastern_date_translations_faq_and_repeat_build(self):
        rows = self.records()
        result = MODULE.render((ROOT / 'index.html').read_text(), rows)
        for text in ('Last refreshed October 17, 2026', '마지막 새로 고침 2026년 10월 17일',
                     'Última actualización: 17 de octubre de 2026', '<time data-schedule-refresh-date>October 17, 2026</time>'):
            self.assertIn(text, result)
        self.assertEqual(MODULE.render(result, rows), result)

    def test_failed_import_cannot_claim_freshness(self):
        rows = self.records()
        rows[0]['success'] = 'false'
        with self.assertRaises(ValueError):
            MODULE.render((ROOT / 'index.html').read_text(), rows)

    def test_failed_refresh_preserves_published_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = root / 'supporting_files/extraction/gtfs_import_metadata.csv'
            metadata.parent.mkdir(parents=True)
            page = root / 'index.html'
            original = MODULE.render((ROOT / 'index.html').read_text(), self.records())
            page.write_text(original)
            rows = self.records()
            rows[0].update(success='false', imported_at='2026-10-19T12:00:00+00:00')
            with metadata.open('w') as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with patch.object(MODULE, 'ROOT', root), self.assertRaises(ValueError):
                MODULE.main()
            self.assertEqual(page.read_text(), original)

    def test_success_updates_all_languages_and_removes_old_notices(self):
        source = (ROOT / 'index.html').read_text()
        rows = self.records()
        for row in rows:
            row['imported_at'] = '2027-01-01T01:00:00+00:00'
        result = MODULE.render(source, rows)
        for date in ('December 31, 2026', '31 de diciembre de 2026', '2026년 12월 31일'):
            self.assertIn('<time data-schedule-refresh-date>' + date + '</time>', result)
        import re
        entries = re.findall(r'\{ id: "when-was-the-data-most-recently-refreshed"[^\n]*', result)
        self.assertEqual(len(entries), 3)
        for entry in entries:
            self.assertIn('open: true', entry)
            self.assertEqual(entry.count('<p>'), 3)
            self.assertNotIn('<ul>', entry)
            self.assertNotIn('<a ', entry)
            self.assertNotIn('October', entry)
