"""Valmistab olemasolevast CSV-st ja Anki pakist veebitööriista andmed."""
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"


def main():
    rows = list(csv.DictReader((ROOT / "taimed.csv").open(encoding="utf-8-sig")))
    (OUT / "pildid").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ROOT / "aednik_4.apkg") as archive, tempfile.TemporaryDirectory() as temporary:
        db = Path(temporary) / "collection.anki2"
        db.write_bytes(archive.read("collection.anki2"))
        with sqlite3.connect(db) as connection:
            notes = {guid: fields.split("\x1f") for guid, fields in connection.execute("SELECT guid, flds FROM notes")}
        media = {name: key for key, name in json.loads(archive.read("media")).items()}
        plants = []
        for row in rows:
            stable = "aednik_" + hashlib.sha256(row["id"].encode()).hexdigest()[:20] + ".jpg"
            source = ""
            picture = ""
            raw = None
            fields = notes.get(row["id"], [])
            match = re.search(r'src="([^"]+)"', fields[0]) if fields else None
            if match:
                if match[1] not in media:
                    raise ValueError(f"Kaardipakist puudub pilt: {match[1]}")
                raw = archive.read(media[match[1]])
                source = html.unescape(fields[4]) if len(fields) > 4 else ""
            if raw:
                with Image.open(io.BytesIO(raw)) as image:
                    image.thumbnail((900, 900))
                    image.convert("RGB").save(OUT / "pildid" / stable, "JPEG", quality=82, optimize=True)
                picture = "pildid/" + stable
            plants.append({"id": row["id"], "group": row["kategooria"], "latin": row["ladina"],
                           "estonian": row["eesti"], "image": picture, "source": source})
    assert len(plants) == len({plant["id"] for plant in plants}) == 419
    assert all((OUT / plant["image"]).is_file() for plant in plants if plant["image"])
    (OUT / "taimed.js").write_text("window.PLANTS = " + json.dumps(plants, ensure_ascii=False) + ";\n")
    paths = ["./", "index.html", "app.js", "study.js", "style.css", "taimed.js", "manifest.webmanifest", "icon.svg"]
    paths += [plant["image"] for plant in plants if plant["image"]]
    (OUT / "offline.json").write_text(json.dumps(paths, ensure_ascii=False))
    print(f"{len(plants)} kirjet, {sum(bool(p['image']) for p in plants)} pildiga")


if __name__ == "__main__":
    main()
