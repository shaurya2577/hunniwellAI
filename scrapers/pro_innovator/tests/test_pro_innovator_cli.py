#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import run_pro_innovator


class ProInnovatorCliTests(unittest.TestCase):
    def test_parser_supports_live_and_csv_only_modes(self):
        parser = run_pro_innovator.build_parser()

        args = parser.parse_args(
            ["--live", "--csv-only", "--output-dir", "/tmp/pro", "--test-one"]
        )

        self.assertTrue(args.live)
        self.assertTrue(args.csv_only)
        self.assertEqual(Path("/tmp/pro"), args.output_dir)
        self.assertTrue(args.test_one)


if __name__ == "__main__":
    unittest.main()
