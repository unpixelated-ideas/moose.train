"""Import fixed adult via fares from saved official MTA /fares responses.

Usage: python supporting_files/scripts/import_lirr_via_fares.py RESPONSE_DIRECTORY
The files must be unmodified JSON responses from
https://backend-unified.mylirr.org/fares?from=CODE&to=CODE&time=UNIX
with Accept-Version: 3.0. No network request is made by this importer or by fare display.
"""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]


def import_responses(directory, root=ROOT):
    path = root / 'supporting_files/reference/lirr_fares.json'
    data = json.loads(path.read_text())
    stations = json.loads((root / 'supporting_files/reference/lirr_stations.json').read_text())
    source_ids = {s['sourceStopId']: s['id'] for s in stations}
    with (root / 'supporting_files/source_gtfs/lirr/feed/stops.txt').open() as handle:
        codes = {s['stop_code']: source_ids.get(s['stop_id']) for s in csv.DictReader(handle)}
    matrix = {}
    sources = {}
    for response in sorted(Path(directory).glob('*.json')):
        payload = json.loads(response.read_text())
        origin, destination = payload.get('fare_origin'), payload.get('fare_destination')
        a, b = [data['stationZones'].get(codes.get(c)) for c in (origin, destination)]
        if not a or not b:
            raise ValueError(f'Missing station zones: {response.name}')
        for fare in payload.get('fares', []):
            via = fare.get('via_station')
            zone = data['stationZones'].get(codes.get(via))
            if not zone or fare.get('rider_category') not in ('ALL', 'ADULT') or fare.get('ticket_type') != 'ONE_WAY' or fare.get('onboard'):
                continue
            if fare['ticket_name'] not in ('Peak', 'Off-Peak'):
                continue
            key = f'{min(a,b)}:{max(a,b)}:{zone}'
            period = 'peak' if fare['valid_peak'] else 'offPeak'
            amount = fare['cost']
            if type(amount) is not int or amount <= 0:
                raise ValueError(f'Invalid fare: {response.name}')
            previous = matrix.setdefault(key, {}).get(period)
            if previous is not None and previous != amount:
                raise ValueError(f'Conflicting published fares: {key} {period}')
            matrix[key][period] = amount
            sources.setdefault(key, {'from': origin, 'to': destination, 'via': via})
    if not matrix or any(set(values) != {'peak', 'offPeak'} for values in matrix.values()):
        raise ValueError('Incomplete adult via fare matrix')
    data['viaOneWay'] = dict(sorted(matrix.items()))
    data['viaSource'] = {'url': 'https://backend-unified.mylirr.org/fares', 'retrievedDate': '2026-10-18', 'samples': dict(sorted(sources.items()))}
    path.write_text(json.dumps(data, indent=2) + '\n')
    html = root / 'index.html'
    content, count = re.subn(r'    const LIRR_FARE_DATA = [^\n]+;', lambda m: '    const LIRR_FARE_DATA = ' + json.dumps(data) + ';', html.read_text())
    if count != 1:
        raise ValueError('Missing embedded fare data')
    html.write_text(content)
    return len(matrix)


if __name__ == '__main__':
    print(f'Imported {import_responses(sys.argv[1])} adult via fare classes')
