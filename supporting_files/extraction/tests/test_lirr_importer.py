import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from test_gtfs_importer import base_files, write_gtfs_zip, station_id_for
from gtfs_importer import default_feed_configs, import_feed

class LirrImportTests(unittest.TestCase):
    def test_shared_station_ids_source_identity_and_overnight_restrictions(self):
        config = next(c for c in default_feed_configs() if c.feed_id == 'lirr')
        files = base_files()
        files['trips.txt'][0].update(trip_headsign='Penn Station', peak_offpeak='0')
        files['stops.txt'][0].update(stop_id='349',stop_name='Grand Central')
        files['stops.txt'][1].update(stop_id='237',stop_name='Penn Station')
        files['stop_times.txt'][0].update(stop_id='349',departure_time='24:05:00',arrival_time='24:05:00',pickup_type='1')
        files['stop_times.txt'][1].update(stop_id='237',departure_time='25:05:00',arrival_time='25:05:00')
        files['stops.txt'].append(dict(files['stops.txt'][0],stop_id='86',stop_name='Hillside Facility'))
        files['stop_times.txt'].append(dict(files['stop_times.txt'][0],stop_id='86',stop_sequence='3',departure_time='26:05:00',arrival_time='26:05:00'))
        with TemporaryDirectory() as directory:
            root=Path(directory)
            write_gtfs_zip(root,'lirr',config.zip_name(),files)
            result=import_feed(root,config,station_id_for,download=False)
            self.assertFalse(result.errors)
            self.assertEqual([row['station_id'] for row in result.rows],['GCT','NYP'])
            self.assertEqual(result.rows[0]['departure_time'],'24:05')
            self.assertIn('gtfs_stop_id=349',result.rows[0]['raw_notes'])
            self.assertIn('pickup_type=1',result.rows[0]['raw_notes'])
            self.assertIn('gtfs_route_id=R1',result.rows[0]['raw_notes'])
            self.assertIn('peak_offpeak=0',result.rows[0]['raw_notes'])
            self.assertEqual(result.normalized['stops'][0]['feed_id'],'lirr')

if __name__ == '__main__':
    unittest.main()
