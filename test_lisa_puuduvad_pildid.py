import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import lisa_puuduvad_pildid as script


class MissingImagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = {"id": "stable", "nimi": "näidistaim", "kindel": True,
                       "pildi_url": "https://example.com/photo.jpg",
                       "allika_url": "https://example.com/source", "allikas": "Autor; CC BY",
                       "markus": "Üks rühma näide", "litsents": "CC BY 4.0"}
        self.row = {"id": "stable", "ladina": "Example species", "eesti": "näidistaim",
                    "kategooria": "Püsililled"}
        self.source["fail"] = script.pakk.image_filename(self.row)
        for name, value in [("IMG_DIR", self.root), ("META", self.root / "_allikad.json")]:
            patcher = patch.object(script.pakk, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(script.time, "sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_manifest_rejects_wrong_filename_before_download(self):
        path = self.root / "sources.json"
        for bad in [dict(self.source, fail="wrong.jpg"), dict(self.source, pildi_url="")]:
            path.write_text(json.dumps([bad]), encoding="utf-8")
            with patch.object(script.pakk, "read_rows", return_value=[self.row]), self.assertRaises(ValueError):
                script.read_sources(path)

    def test_download_preserves_attribution_and_example_note(self):
        data = io.BytesIO()
        Image.new("RGB", (8, 8), "green").save(data, format="JPEG")
        meta = {}
        with patch.object(script.pakk.urllib.request, "urlopen", return_value=io.BytesIO(data.getvalue())), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(script.add_images([self.source], meta), (1, 0))
        entry = meta[self.source["fail"]]
        self.assertIn("Üks rühma näide", entry["allikas"])
        self.assertIn(self.source["allika_url"], entry["allikas"])
        self.assertIn("CC BY 4.0", entry["allikas"])
        self.assertTrue(entry["käsitsi"])
        self.assertEqual(entry["sha256"], hashlib.sha256((self.root / self.source["fail"]).read_bytes()).hexdigest())
        with patch.object(script.pakk, "find_image") as lookup:
            self.assertEqual(script.pakk.ensure_image(self.row, meta, set()), self.source["fail"])
            lookup.assert_not_called()

    def test_uncertain_entry_and_existing_photo_are_skipped(self):
        Image.new("RGB", (8, 8), "green").save(self.root / self.source["fail"])
        with patch.object(script.pakk, "download") as download, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(script.add_images([dict(self.source, kindel=False), self.source], {}), (0, 0))
            download.assert_not_called()

    def test_failed_download_does_not_add_attribution(self):
        with patch.object(script.pakk, "download", side_effect=ValueError("not an image")), \
                contextlib.redirect_stdout(io.StringIO()):
            meta = {}
            self.assertEqual(script.add_images([self.source], meta), (0, 1))
            self.assertEqual(meta, {})

    def test_commons_original_is_replaced_with_standard_thumbnail(self):
        original = "https://upload.wikimedia.org/wikipedia/commons/f/f2/Delphinium_cultorum_cv.01.JPG"
        expected = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Delphinium_cultorum_cv.01.JPG/960px-Delphinium_cultorum_cv.01.JPG"
        response = {"query": {"pages": [{"imageinfo": [{"thumburl": expected}]}]}}
        with patch.object(script.pakk, "download", side_effect=ValueError("test ends before write")) as download, \
                patch.object(script.pakk, "get_json", return_value=response) as metadata, \
                contextlib.redirect_stdout(io.StringIO()):
            script.add_images([dict(self.source, pildi_url=original)], {})
        self.assertEqual(download.call_args.args[0], expected)
        self.assertIn("iiurlwidth=960", metadata.call_args.args[0])
        self.assertEqual(self.sleep.call_count, 2)

    def test_429_stops_before_requesting_next_photo(self):
        error = urllib.error.HTTPError("https://example.com/photo", 429, "Too many requests", {}, None)
        second = dict(self.source, id="second", fail="second.jpg")
        with patch.object(script.pakk, "download", side_effect=error) as download, \
                contextlib.redirect_stdout(io.StringIO()):
            script.add_images([self.source, second], {})
        self.assertEqual(download.call_count, 1)

    def test_commons_429_from_metadata_stops_before_any_image_request(self):
        error = urllib.error.HTTPError("https://commons.wikimedia.org/w/api.php", 429,
                                       "Too many requests", {"Retry-After": "120"}, None)
        original = "https://upload.wikimedia.org/wikipedia/commons/a/ab/example.jpg"
        with patch.object(script.pakk, "get_json", side_effect=error) as metadata, \
                patch.object(script.pakk, "download") as download, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(script.add_images([dict(self.source, pildi_url=original), self.source], {}), (0, 1))
        self.assertEqual(metadata.call_count, 1)
        download.assert_not_called()
        self.assertIn("Retry-After: 120", output.getvalue())

    def test_small_commons_original_is_not_forced_to_upscale(self):
        original = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Thrips_tabaci.jpg"
        response = {"query": {"pages": [{"imageinfo": [{"url": original, "width": 261}]}]}}
        with patch.object(script.pakk, "get_json", return_value=response):
            self.assertEqual(script.image_url(dict(self.source, pildi_url=original)), original)

    def test_existing_photos_make_no_metadata_request_and_need_no_wait(self):
        Image.new("RGB", (8, 8), "green").save(self.root / self.source["fail"])
        with patch.object(script.pakk, "get_json") as metadata, contextlib.redirect_stdout(io.StringIO()):
            script.add_images([self.source], {})
        metadata.assert_not_called()
        self.sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
