"""Prevent reuse of a matrix after its points, bytes or flight order change."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('pipeline', Path(__file__).resolve().parents[1]/'run_pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

class CacheChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prepared = self.root/'data/lhr_fra_prepared'
        self.matrix = self.root/'data/lhr_fra_hausdorff'
        self.prepared.mkdir(parents=True)
        self.matrix.mkdir(parents=True)
        (self.prepared/'flight_points_clean.csv.gz').write_bytes(b'fixture input bytes')
        (self.prepared/'accepted_flights.csv').write_text('flight_id\nA\nB\n')
        (self.matrix/'hausdorff_flight_ids.csv').write_text('matrix_index,flight_id\n0,A\n1,B\n')
        (self.matrix/'hausdorff_distance_matrix_km.npy').write_bytes(b'fixture matrix bytes')
        (self.matrix/'matrix.sha256').write_text(pipeline.digest(self.matrix/'hausdorff_distance_matrix_km.npy'))
        (self.matrix/'matrix_report.json').write_text(json.dumps({'clean_points_sha256':pipeline.digest(self.prepared/'flight_points_clean.csv.gz')}))
    def tearDown(self):
        self.temp.cleanup()
    def test_changed_points_invalidate_cache(self):
        self.assertTrue(pipeline.matrix_is_current(self.root))
        (self.prepared/'flight_points_clean.csv.gz').write_bytes(b'changed')
        self.assertFalse(pipeline.matrix_is_current(self.root))
    def test_changed_matrix_invalidates_cache(self):
        (self.matrix/'hausdorff_distance_matrix_km.npy').write_bytes(b'changed')
        self.assertFalse(pipeline.matrix_is_current(self.root))
    def test_changed_flight_order_invalidates_cache(self):
        (self.matrix/'hausdorff_flight_ids.csv').write_text('matrix_index,flight_id\n0,B\n1,A\n')
        self.assertFalse(pipeline.matrix_is_current(self.root))

if __name__ == '__main__':
    unittest.main()
