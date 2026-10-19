"""Render public freshness labels from successful imports, never the build clock."""
import csv
import datetime as dt
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
MONTHS = ("January February March April May June July August September October November December").split()
SPANISH_MONTHS = ("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre").split()


def format_date(day, language):
    if language == "ko":
        return f"{day.year}년 {day.month}월 {day.day}일"
    if language == "es":
        return f"{day.day} de {SPANISH_MONTHS[day.month - 1]} de {day.year}"
    return f"{MONTHS[day.month - 1]} {day.day}, {day.year}"


def render(html, metadata):
    if len(metadata) != 5 or {row['feed_id'] for row in metadata} != {"mnr", "hartford", "sle", "amtrak", "lirr"}:
        raise ValueError("Expected five import records")
    if any(row['success'] != 'true' for row in metadata):
        raise ValueError("Cannot label failed imports as refreshed")
    # A complete refresh is only as fresh as its oldest product.
    day = min(dt.datetime.fromisoformat(row['imported_at']).astimezone(
        ZoneInfo('America/New_York')).date() for row in metadata)
    dates = {language: format_date(day, language) for language in ('en', 'ko', 'es')}
    labels = [f"Last refreshed {dates['en']}", f"마지막 새로 고침 {dates['ko']}",
              f"Última actualización: {dates['es']}"]
    html, count = re.subn(r'(data-i18n="updateLogDataRefresh">)[^<]*(</span>)',
                         lambda match: match[1] + labels[0] + match[2], html)
    if count != 1:
        raise ValueError("Missing update log freshness label")
    index = iter(labels)
    html, count = re.subn(r'updateLogDataRefresh: "[^"]*"',
                         lambda match: 'updateLogDataRefresh: "' + next(index) + '"', html)
    if count != 3:
        raise ValueError("Expected freshness translations in English, Korean, Spanish")
    # Both FAQ views use index.html. Only the date changes after a successful
    # import; keep the localized copy and disclosure structure intact.
    languages = iter(('en', 'ko', 'es'))

    def faq(match):
        language = next(languages)
        content, count = re.subn(
            r'(<time data-schedule-refresh-date>)[^<]*(</time>)',
            lambda date: date[1] + dates[language] + date[2], match[2])
        if count != 1:
            raise ValueError("Expected one successful refresh date per FAQ translation")
        return match[1] + content + match[3]

    html, count = re.subn(r'(\{ id: "when-was-the-data-most-recently-refreshed"[^\n]*?content: `)([^`]*)(`)', faq, html)
    if count != 3:
        raise ValueError("Expected three shared FAQ freshness entries")
    return html


def main():
    with (ROOT / 'supporting_files/extraction/gtfs_import_metadata.csv').open() as handle:
        metadata = list(csv.DictReader(handle))
    path = ROOT / 'index.html'
    path.write_text(render(path.read_text(), metadata))


if __name__ == '__main__':
    main()
