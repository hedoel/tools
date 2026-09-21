import os
import unittest
from unittest.mock import patch, MagicMock
from core.edge_cdp import get_driver_path, get_edge_version, EdgeCDPManager

class TestEdgeCDP(unittest.TestCase):
    def test_get_driver_path_found(self):
        # Local repo driver should be found
        p = get_driver_path()
        self.assertIsNotNone(p)
        self.assertTrue(os.path.exists(p))

    def test_get_driver_path_not_found(self):
        # If no file exists, it should return None, not a phantom string
        with patch("os.path.exists", return_value=False), patch("shutil.which", return_value=None):
            p = get_driver_path()
            self.assertIsNone(p)

    def test_get_edge_version(self):
        major, full = get_edge_version()
        if major is not None:
            self.assertIsInstance(major, int)
            self.assertIsInstance(full, str)
            self.assertTrue(full.startswith(str(major)))

    def test_download_progress_callback(self):
        # Verify EdgeCDPManager progress callback propagation
        msgs = []
        mgr = EdgeCDPManager(progress_callback=lambda m, p: msgs.append((m, p)))
        mgr.progress("测试中", 50)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0], ("测试中", 50))

if __name__ == "__main__":
    unittest.main()
