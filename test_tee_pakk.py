import contextlib
import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import tee_pakk as script


def image_bytes(format="JPEG"):
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "green").save(stream, format=format)
    return stream.getvalue()


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root / "pildid"
        self.images.mkdir()
        for name, value in [("IMG_DIR", self.images), ("META", self.images / "_allikad.json")]:
            patcher = patch.object(script, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.row = {"id": "stable-id", "ladina": "Aconitum napellus",
                    "eesti": "sinine käoking", "kategooria": "Püsililled"}

    def test_every_name_and_image_combination_has_a_card(self):
        model = script.make_model()
        for latin, eesti, picture, expected in [
            ("Latin", "Eesti", "a.jpg", [0, 1]),
            ("Latin", "Eesti", "", [1]),
            ("", "Eesti", "a.jpg", [0]),
            ("Latin", "", "a.jpg", [0]),
            ("", "Eesti", "", [2]),
            ("Latin", "", "", [2]),
        ]:
            with self.subTest(latin=latin, eesti=eesti, picture=picture):
                row = dict(self.row, ladina=latin, eesti=eesti)
                note = script.make_note(row, picture, "", model)
                self.assertEqual([card.ord for card in note.cards], expected)

    def test_inat_skips_unrelated_first_result(self):
        response = {"results": [
            {"name": "Wrong species", "default_photo": {"medium_url": "wrong"}},
            {"name": "Aconitum napellus", "default_photo": {"medium_url": "right"}},
        ]}
        with patch.object(script, "get_json", return_value=response):
            self.assertEqual(script.inat("Aconitum napellus")[0], "right")
            self.assertIsNone(script.inat("Another species"))

    def test_inat_common_name_must_match(self):
        response = {"results": [{"name": "Rhododendron", "preferred_common_name": "rodo",
                                  "default_photo": {"medium_url": "photo"}}]}
        with patch.object(script, "get_json", return_value=response):
            self.assertIsNone(script.inat("asalea", "et"))
            self.assertEqual(script.inat("rodo", "et")[0], "photo")

    def test_hybrid_marker_and_case_are_normalized(self):
        self.assertEqual(script.normalized("  Mentha x piperita "),
                         script.normalized("MENTHA × PIPERITA"))

    def test_wikipedia_rejects_redirect_and_disambiguation(self):
        with patch.object(script, "get_json") as lookup:
            lookup.return_value = {"type": "standard", "title": "Wrong species",
                                   "thumbnail": {"source": "wrong"}}
            self.assertIsNone(script.wiki("Aconitum napellus", "en"))
            lookup.return_value.update(type="disambiguation", title="Aconitum napellus")
            self.assertIsNone(script.wiki("Aconitum napellus", "en"))
            lookup.return_value["type"] = "standard"
            self.assertEqual(script.wiki("Aconitum napellus", "en")[0], "wrong")

    def test_all_latin_aliases_are_tried(self):
        with patch.object(script, "inat", side_effect=lambda name, locale: ("photo", "source")
                          if name == "Lamprocapnos" else None) as lookup, \
                patch.object(script, "wiki", return_value=None), patch.object(script.time, "sleep"):
            self.assertEqual(script.find_image("Dicentra, Lamprocapnos", "murtudsüda")[0], "photo")
            self.assertEqual([call.args[0] for call in lookup.call_args_list], ["Dicentra", "Lamprocapnos"])

    def test_distinct_subjects_have_distinct_images_and_searches(self):
        rows = script.read_rows(script.HERE / "taimed.csv")
        ambiguous = script.ambiguous_names(rows)
        for latin in ["Rhododendron", "Brassica oleracea"]:
            entries = [row for row in rows if row["ladina"] == latin]
            self.assertEqual(len(entries), 2)
            self.assertNotEqual(script.image_filename(entries[0]), script.image_filename(entries[1]))
            self.assertEqual(script.image_query(entries[0], ambiguous), ("", entries[0]["eesti"]))
            self.assertEqual(script.image_query(entries[1], ambiguous), ("", entries[1]["eesti"]))
        self.assertEqual(script.image_query(dict(self.row, pildiotsing="Chosen taxon"), ambiguous),
                         ("Chosen taxon", ""))

    def test_failed_download_does_not_leave_or_replace_file(self):
        class BrokenResponse(io.BytesIO):
            def read(self, size=-1):
                if self.tell():
                    raise OSError("connection interrupted")
                return super().read(4)

        path = self.images / "photo.jpg"
        for old in [None, image_bytes()]:
            with self.subTest(existing=old is not None):
                if old is not None:
                    path.write_bytes(old)
                with patch.object(script.urllib.request, "urlopen", return_value=BrokenResponse(image_bytes())):
                    with self.assertRaises(OSError):
                        script.download("https://example.com/photo", path)
                self.assertEqual(path.read_bytes() if path.exists() else None, old)
                self.assertEqual(list(self.images.iterdir()), [path] if old else [])

    def test_empty_truncated_and_html_downloads_are_rejected(self):
        corrupt_png = bytearray(image_bytes("PNG"))
        corrupt_png[corrupt_png.index(b"IDAT") + 4] ^= 0xff
        for data in [b"", b"<html>Error</html>", image_bytes()[:40], bytes(corrupt_png)]:
            with self.subTest(data=data[:20]), \
                    patch.object(script.urllib.request, "urlopen", return_value=io.BytesIO(data)):
                with self.assertRaises(ValueError):
                    script.download("https://example.com/photo", self.images / "photo.jpg")
                self.assertEqual(list(self.images.iterdir()), [])

    def test_png_download_becomes_valid_jpeg(self):
        path = self.images / "photo.jpg"
        with patch.object(script.urllib.request, "urlopen", return_value=io.BytesIO(image_bytes("PNG"))):
            script.download("https://example.com/photo", path)
        self.assertTrue(script.valid_image(path))
        with Image.open(path) as image:
            self.assertEqual(image.format, "JPEG")

    def test_zero_byte_cache_is_retried(self):
        path = self.images / script.image_filename(self.row)
        path.touch()
        with patch.object(script, "find_image", return_value=("https://example.com/a", "source")), \
                patch.object(script.urllib.request, "urlopen", return_value=io.BytesIO(image_bytes())):
            self.assertEqual(script.ensure_image(self.row, {}, set()), path.name)
        self.assertTrue(script.valid_image(path))

    def test_checked_cache_is_reused_and_renamed_subject_is_rechecked(self):
        meta = {}
        with patch.object(script, "find_image", return_value=("https://example.com/a", "source")) as lookup, \
                patch.object(script.urllib.request, "urlopen", return_value=io.BytesIO(image_bytes())):
            fname = script.ensure_image(self.row, meta, set())
            self.assertEqual(script.ensure_image(self.row, meta, set()), fname)
            self.assertEqual(lookup.call_count, 1)
        with patch.object(script, "find_image", return_value=None) as lookup:
            changed = dict(self.row, ladina="Corrected name")
            self.assertEqual(script.ensure_image(changed, meta, set()), "")
            lookup.assert_called_once()

    def test_manual_image_is_preserved_and_attribution_reset(self):
        path = self.images / script.image_filename(self.row)
        path.write_bytes(image_bytes())
        meta = {path.name: {"sha256": "old digest", "allikas": "Old photographer"}}
        with patch.object(script, "find_image") as lookup:
            self.assertEqual(script.ensure_image(self.row, meta, set()), path.name)
            lookup.assert_not_called()
        self.assertTrue(meta[path.name]["käsitsi"])
        self.assertEqual(meta[path.name]["allikas"], "Käsitsi lisatud pilt")

    def test_legacy_unverified_file_is_not_used(self):
        key = self.row["ladina"]
        legacy = self.images / ("aednik_" + hashlib.md5(key.encode()).hexdigest()[:10] + ".jpg")
        legacy.write_bytes(image_bytes())
        with patch.object(script, "find_image", return_value=None) as lookup:
            self.assertEqual(script.ensure_image(self.row, {}, set()), "")
            lookup.assert_called_once()
        self.assertTrue(legacy.exists())

    def test_editing_names_and_category_keeps_identity_and_image_filename(self):
        changed = dict(self.row, ladina="Corrected name", eesti="Parandatud nimi", kategooria="Uus rühm")
        model = script.make_model()
        self.assertEqual(script.make_note(self.row, "", "", model).guid,
                         script.make_note(changed, "", "", model).guid)
        self.assertEqual(script.image_filename(self.row), script.image_filename(changed))

    def test_ids_match_existing_package(self):
        rows = script.read_rows(script.HERE / "taimed.csv")
        with zipfile.ZipFile(script.HERE / "aednik_4.apkg") as archive:
            archive.extract("collection.anki2", self.root)
        with contextlib.closing(sqlite3.connect(self.root / "collection.anki2")) as db:
            guids = {row[0] for row in db.execute("select guid from notes")}
        self.assertEqual({row["id"] for row in rows}, guids)

    def test_duplicate_and_missing_ids_are_rejected(self):
        path = self.root / "invalid.csv"
        for ids in [("",), ("same", "same")]:
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["id", "ladina", "eesti", "kategooria"])
                writer.writeheader()
                for id in ids:
                    writer.writerow(dict(self.row, id=id))
            with self.assertRaises(ValueError):
                script.read_rows(path)

    def test_real_list_builds_a_package_with_no_cardless_notes_even_without_images(self):
        rows = script.read_rows(script.HERE / "taimed.csv")
        with patch.object(script, "HERE", self.root), patch.object(script, "read_rows", return_value=rows), \
                patch.object(script, "find_image", return_value=None), contextlib.redirect_stdout(io.StringIO()) as output:
            script.main()
        with zipfile.ZipFile(self.root / "aednik_4.apkg") as archive:
            archive.extract("collection.anki2", self.root)
            self.assertEqual(json.loads(archive.read("media")), {})
        with contextlib.closing(sqlite3.connect(self.root / "collection.anki2")) as db:
            self.assertEqual(db.execute("select count(*) from notes").fetchone()[0], 419)
            self.assertEqual(db.execute("select count(*) from cards").fetchone()[0], 419)
            self.assertEqual(db.execute("select count(*) from notes where id not in (select nid from cards)").fetchone()[0], 0)
            self.assertEqual(db.execute("select count(*) from cards where ord=2").fetchone()[0], 48)
        self.assertIn("0 kaartideta kirjet", output.getvalue())


if __name__ == "__main__":
    unittest.main()
