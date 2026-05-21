#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from platforms.innovator.pro_innovator.pdf_build import (
    append_company_result,
    build_pdf_from_images,
    init_run_manifest,
    load_run_manifest,
)


class ProInnovatorManifestTests(unittest.TestCase):
    def test_manifest_tracks_company_capture_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            init_run_manifest(manifest_path, run_label="test-run")
            append_company_result(
                manifest_path,
                {
                    "company_name": "MediVault",
                    "status": "captured",
                    "page_count": 16,
                    "pdf_path": "/tmp/MediVault.pdf",
                },
            )

            data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual("test-run", data["run_label"])
        self.assertEqual(1, len(data["companies"]))
        self.assertEqual("MediVault", data["companies"][0]["company_name"])
        self.assertEqual("captured", data["companies"][0]["status"])

    def test_append_company_result_updates_existing_company_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            init_run_manifest(manifest_path, run_label="test-run")
            append_company_result(
                manifest_path,
                {
                    "company_name": "MediVault",
                    "row_id": "18945",
                    "status": "failed",
                    "page_count": 0,
                },
            )
            append_company_result(
                manifest_path,
                {
                    "company_name": "MediVault",
                    "row_id": "18945",
                    "status": "captured",
                    "page_count": 16,
                },
            )

            data = load_run_manifest(manifest_path)

        self.assertEqual(1, len(data["companies"]))
        self.assertEqual("captured", data["companies"][0]["status"])

    def test_build_pdf_from_images_writes_output_file(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_a = tmp_path / "a.png"
            image_b = tmp_path / "b.png"
            pdf_path = tmp_path / "deck.pdf"

            Image.new("RGB", (40, 40), "red").save(image_a)
            Image.new("RGB", (40, 40), "blue").save(image_b)

            build_pdf_from_images([str(image_a), str(image_b)], pdf_path)

            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
