import importlib.util
from pathlib import Path
import unittest

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
                     'Última actualización: 17 de octubre de 2026', 'last imported on October 17, 2026'):
            self.assertIn(text, result)
        self.assertEqual(MODULE.render(result, rows), result)

    def test_failed_import_cannot_claim_freshness(self):
        rows = self.records()
        rows[0]['success'] = 'false'
        with self.assertRaises(ValueError):
            MODULE.render((ROOT / 'index.html').read_text(), rows)
