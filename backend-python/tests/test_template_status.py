import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.routers.templates import map_meta_status

class TestTemplateStatusMapping(unittest.TestCase):
    def test_pending_maps_to_submitted(self):
        self.assertEqual(map_meta_status('PENDING'), 'SUBMITTED')
        self.assertEqual(map_meta_status('pending'), 'SUBMITTED')
        self.assertEqual(map_meta_status(None), 'SUBMITTED')
        self.assertEqual(map_meta_status(''), 'SUBMITTED')

    def test_approved_passthrough(self):
        self.assertEqual(map_meta_status('APPROVED'), 'APPROVED')
        self.assertEqual(map_meta_status('approved'), 'APPROVED')

    def test_rejected_passthrough(self):
        self.assertEqual(map_meta_status('REJECTED'), 'REJECTED')
        self.assertEqual(map_meta_status('rejected'), 'REJECTED')

    def test_paused_disabled_passthrough(self):
        self.assertEqual(map_meta_status('PAUSED'), 'PAUSED')
        self.assertEqual(map_meta_status('DISABLED'), 'DISABLED')
        self.assertEqual(map_meta_status('DRAFT'), 'DRAFT')

    def test_unknown_maps_to_submitted(self):
        self.assertEqual(map_meta_status('IN_APPEAL'), 'SUBMITTED')
        self.assertEqual(map_meta_status('PENDING_DELETION'), 'SUBMITTED')

if __name__ == '__main__':
    unittest.main()
