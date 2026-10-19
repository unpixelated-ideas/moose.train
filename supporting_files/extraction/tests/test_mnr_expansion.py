import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from test_gtfs_importer import base_files, write_gtfs_zip, station_id_for
from gtfs_importer import default_feed_configs, import_feed


class MetroNorthExpansionTests(unittest.TestCase):
    def test_both_lines_shared_ids_and_nonpublic_stops(self):
        config = next(c for c in default_feed_configs() if c.feed_id == 'mnr')
        self.assertEqual(config.route_filter.include_route_ids, set('123456'))
        for route_id, service, stop_id, name, canonical in [
            ('1', 'Hudson Line', '18', 'Yonkers', 'YNY'),
            ('1', 'Hudson Line', '33', 'Croton-Harmon', 'CRT'),
            ('1', 'Hudson Line', '51', 'Poughkeepsie', 'POU'),
            ('2', 'Harlem Line', '177', 'Wassaic', 'MNR_177'),
        ]:
            with self.subTest(stop=name), TemporaryDirectory() as directory:
                files = base_files()
                files['routes.txt'][0]['route_id'] = route_id
                files['trips.txt'][0].update(route_id=route_id, peak_offpeak='1')
                files['stops.txt'][0].update(stop_id='1', stop_name='Grand Central')
                files['stops.txt'][1].update(stop_id=stop_id, stop_name=name)
                files['stop_times.txt'][0].update(stop_id='1', pickup_type='1')
                files['stop_times.txt'][1].update(stop_id=stop_id, drop_off_type='1')
                for private_id in ['184', '651']:
                    files['stops.txt'].append(dict(files['stops.txt'][0],stop_id=private_id,stop_name='Maintenance'))
                    files['stop_times.txt'].append(dict(files['stop_times.txt'][0],stop_id=private_id,stop_sequence='3'))
                root = Path(directory)
                write_gtfs_zip(root, 'mnr', config.zip_name(), files)
                result = import_feed(root, config, station_id_for, download=False)
                self.assertFalse(result.errors)
                self.assertEqual(len(result.rows), 2)
                self.assertEqual(result.rows[-1]['station_id'], canonical)
                self.assertEqual(result.rows[-1]['service_name'], service)
                self.assertIn('peak_offpeak=1', result.rows[0]['raw_notes'])
                self.assertIn('pickup_type=1', result.rows[0]['raw_notes'])
                self.assertIn('drop_off_type=1', result.rows[-1]['raw_notes'])

    def test_amtrak_scope_only_adds_shared_hudson_stations(self):
        config = next(c for c in default_feed_configs() if c.feed_id == 'amtrak')
        self.assertTrue({'YNY','CRT','POU'} <= config.in_scope_stop_ids)
        self.assertFalse({'ALB','HUD','RHI'} & config.in_scope_stop_ids)
        self.assertEqual(config.station_id_map['Croton-Harmon'], 'CRT')
        self.assertEqual(config.min_in_scope_stops, 2)
        self.assertEqual(config.route_filter.include_route_types, {'2'})
