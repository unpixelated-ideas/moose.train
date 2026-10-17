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
    if len(metadata) != 4 or {row['feed_id'] for row in metadata} != {"mnr", "hartford", "sle", "amtrak"}:
        raise ValueError("Expected four import records")
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
    # FAQ is shared by index.html and faq.html. Replace the current-import
    # paragraph and receipt-date list; leave dated historical notices intact.
    intros = [
        f"The schedule data in moose.train was last imported on {dates['en']} (US Eastern date). These are published static GTFS schedules, not live train data.",
        f"moose.train의 시간표 데이터는 {dates['ko']}(미국 동부시간 기준)에 마지막으로 가져왔습니다. 게시된 정적 GTFS 시간표이며 실시간 열차 데이터가 아닙니다.",
        f"Los datos de horarios de moose.train se importaron por última vez el {dates['es']} (fecha de EE. UU. Este). Son horarios estáticos GTFS publicados, no datos en vivo."
    ]
    languages = iter(zip(('en', 'ko', 'es'), intros))

    def faq(match):
        language, intro = next(languages)
        receipt = {'en': 'received', 'ko': '수신', 'es': 'recibido'}[language]
        items = []
        for row in metadata:
            imported = dt.datetime.fromisoformat(row['imported_at']).astimezone(ZoneInfo('America/New_York')).date()
            name = {'mnr': 'Metro-North', 'hartford': 'CTrail Hartford Line',
                    'sle': 'CTrail Shore Line East', 'amtrak': 'Amtrak'}[row['feed_id']]
            items.append(f"<li><strong>{name}:</strong> {receipt} {format_date(imported, language)}.</li>")
        content = re.sub(r'^<p>.*?</p>', lambda _: '<p>' + intro + '</p>', match[2], count=1)
        content = re.sub(r'<ul>.*?</ul>', lambda _: '<ul>' + ''.join(items) + '</ul>', content, count=1)
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
