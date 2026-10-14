#!/usr/bin/env python3
"""Teeb taimed.csv põhjal Anki paki koos piltidega.

Kasutus: pip install -r requirements.txt; python3 tee_pakk.py
CSV veerud: id, kategooria, ladina, eesti, pildiotsing.
ID on püsiv: nime või kategooria parandamisel jäta see samaks. Uuele reale
anna uus ID, näiteks uuid.uuid4().hex. Pildiotsing on valikuline täpne nimi.
Sama ladinakeelse nime eri õpiobjekte otsitakse vaikimisi eesti nime järgi.

Pilte saab käsitsi lisada/asendada skripti näidatud failinimega kaustas pildid/.
Vana skripti kontrollimata pildid säilivad, kuid neid automaatselt ei kasutata.
Pildita ja ainult ühe nimega kirje saab nime → õpinimekirja rühma varukaardi.
"""
import csv
import hashlib
import html
import json
import re
import tempfile
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import genanki
from PIL import Image

HERE = Path(__file__).resolve().parent
IMG_DIR = HERE / "pildid"
META = IMG_DIR / "_allikad.json"
UA = {"User-Agent": "aednik-anki/1.0 (personal study deck)"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def valid_image(path):
    try:
        with Image.open(path) as image:
            if image.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                return False
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return False


def download(url, path):
    """Asendab lõpliku faili ainult pärast edukat laadimist ja pildi kontrolli."""
    path = Path(path)
    temporary = None
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as response:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                while chunk := response.read(64 * 1024):
                    stream.write(chunk)
        if not valid_image(temporary):
            raise ValueError("Allalaaditud fail ei ole terve pilt")
        # Kõik meediafailid on päriselt JPEG-id, ka PNG/WebP lähtefaili korral.
        with Image.open(temporary) as image:
            image.convert("RGB").save(temporary, format="JPEG", quality=95)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_meta(meta):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=IMG_DIR,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(meta, stream, ensure_ascii=False, indent=1)
        temporary.replace(META)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def clean_latin(name):
    return re.sub(r"\s[x×]\s", " × ", name).strip()


def normalized(name):
    return " ".join(clean_latin(name).replace("_", " ").casefold().split())


def inat(query, locale=None):
    params = {"q": query, "per_page": 30, "is_active": "true"}
    if locale:
        params["locale"] = locale
    data = get_json("https://api.inaturalist.org/v1/taxa?" + urllib.parse.urlencode(params))
    for taxon in data.get("results", []):
        names = [taxon.get("preferred_common_name", "")] if locale else [taxon.get("name", "")]
        if normalized(query) not in {normalized(name) for name in names}:
            continue
        photo = taxon.get("default_photo") or {}
        if photo.get("medium_url"):
            source = f"{photo.get('attribution', 'iNaturalist')}; iNaturalist: {taxon['name']}"
            return photo["medium_url"], source
    return None


def wiki(title, lang):
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = get_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}")
    # Ümbersuunamise või täpsustuslehe fotot ei võeta kontrollimata vasteks.
    if data.get("type") != "standard" or normalized(data.get("title", "")) != normalized(title):
        return None
    image = (data.get("thumbnail") or {}).get("source")
    return (image, f"Wikipedia ({lang}): {data['title']}") if image else None


def find_image(latin, eesti):
    queries = [(clean_latin(name), None) for name in latin.split(",") if name.strip()]
    first_est = re.split(r"[(,;]", eesti)[0].strip()
    if first_est:
        queries.append((first_est, "et"))
    for query, locale in queries:
        lookups = [(inat, (query, locale))]
        lookups += [(wiki, (query, lang)) for lang in (["et"] if locale else ["en", "et"])]
        for lookup, args in lookups:
            try:
                result = lookup(*args)
            except (OSError, ValueError) as error:
                print(f"\n  Pildiotsing ebaõnnestus ({query}): {error}")
                result = None
            finally:
                time.sleep(1)
            if result:
                return result
    return None


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"id", "kategooria", "ladina", "eesti"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV peab sisaldama veerge {', '.join(sorted(required))}")
        rows = []
        ids = set()
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV real {line} on vale arv veerge")
            row = {key: value.strip() for key, value in row.items()}
            if not row["id"] or row["id"] in ids:
                raise ValueError(f"CSV real {line} puudub ID või see kordub")
            if not row["kategooria"] or not (row["ladina"] or row["eesti"]):
                raise ValueError(f"CSV real {line} puudub kategooria või nimi")
            ids.add(row["id"])
            rows.append(row)
    return rows


def image_filename(row):
    return "aednik_" + hashlib.sha256(row["id"].encode()).hexdigest()[:20] + ".jpg"


def ambiguous_names(rows):
    names = defaultdict(set)
    for row in rows:
        if row["ladina"]:
            names[normalized(row["ladina"])].add(normalized(row["eesti"]))
    return {name for name, est in names.items() if len(est) > 1}


def image_query(row, ambiguous):
    override = row.get("pildiotsing", "")
    if override:
        return override, ""
    if normalized(row["ladina"]) in ambiguous:
        return "", row["eesti"]
    return row["ladina"], row["eesti"]


def ensure_image(row, meta, ambiguous):
    fname = image_filename(row)
    path = IMG_DIR / fname
    query = list(image_query(row, ambiguous))
    entry = meta.get(fname, {})
    if valid_image(path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not entry or digest != entry.get("sha256"):
            # Käsitsi lisatud/asendatud pilt on kasutaja valik, vana omistus ei kehti.
            meta[fname] = {"nimi": row["ladina"] or row["eesti"], "käsitsi": True,
                           "allikas": "Käsitsi lisatud pilt", "sha256": digest}
            save_meta(meta)
            return fname
        if entry.get("käsitsi") or (entry.get("päring") == query and entry.get("vaste_kontrollitud")):
            return fname

    result = find_image(*query)
    if result:
        try:
            download(result[0], path)
        except (OSError, ValueError) as error:
            print(f"  Allalaadimine ebaõnnestus: {error}")
        else:
            meta[fname] = {"nimi": row["ladina"] or row["eesti"], "url": result[0],
                           "allikas": result[1], "päring": query, "vaste_kontrollitud": True,
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            save_meta(meta)
            return fname
    return ""


def make_model():
    return genanki.Model(
        1607392319,
        "Aednik taim (pilt + nimed)",
        fields=[{"name": name} for name in ["Pilt", "Ladina", "Eesti", "Kategooria", "Allikas", "Varunimi"]],
        templates=[
            {
                "name": "Pilt → nimi",
                "qfmt": "{{#Pilt}}<div class=cat>{{Kategooria}}</div>{{Pilt}}<div class=q>Mis on pildil?</div>{{/Pilt}}",
                "afmt": "{{FrontSide}}<hr id=answer><div class=lat>{{Ladina}}</div><div class=est>{{Eesti}}</div><div class=src>{{Allikas}}</div>",
            },
            {
                "name": "Eesti → ladina",
                "qfmt": "{{#Ladina}}{{#Eesti}}<div class=cat>{{Kategooria}}</div><div class=est>{{Eesti}}</div><div class=q>Ladinakeelne nimi?</div>{{/Eesti}}{{/Ladina}}",
                "afmt": "{{FrontSide}}<hr id=answer><div class=lat>{{Ladina}}</div>{{Pilt}}",
            },
            {
                "name": "Nimi → rühm (pildita kirje)",
                "qfmt": "{{#Varunimi}}<div>{{Varunimi}}</div><div class=q>Millisesse õpinimekirja rühma see kuulub?</div>{{/Varunimi}}",
                "afmt": "{{FrontSide}}<hr id=answer><div>{{Kategooria}}</div>",
            },
        ],
        css=""".card{font-family:system-ui,sans-serif;text-align:center;font-size:20px}
img{max-width:100%;max-height:60vh;border-radius:8px}
.cat{font-size:13px;color:#888;margin-bottom:8px}
.q{margin-top:10px;color:#666}
.lat{font-style:italic;font-size:24px;margin:8px 0}
.est{font-size:22px}
.src{font-size:11px;color:#999;margin-top:12px}""",
    )


def make_note(row, fname, source, model):
    latin, eesti, cat = row["ladina"], row["eesti"], row["kategooria"]
    fallback = (eesti or latin) if not fname and not (latin and eesti) else ""
    return genanki.Note(
        model=model,
        fields=[f'<img src="{fname}">' if fname else "", html.escape(latin), html.escape(eesti),
                html.escape(cat), html.escape(source), html.escape(fallback)],
        guid=row["id"],
        tags=[re.sub(r"\W+", "_", cat)],
    )


def main():
    rows = read_rows(HERE / "taimed.csv")
    IMG_DIR.mkdir(exist_ok=True)
    meta = {}
    if META.exists():
        with META.open(encoding="utf-8") as stream:
            meta = json.load(stream)
    model = make_model()
    ambiguous = ambiguous_names(rows)
    decks, media, missing = {}, set(), []
    card_count = fallback_count = 0
    for i, row in enumerate(rows, 1):
        key, cat = row["ladina"] or row["eesti"], row["kategooria"]
        print(f"[{i}/{len(rows)}] {key}", flush=True)
        fname = ensure_image(row, meta, ambiguous)
        if fname:
            media.add(str(IMG_DIR / fname))
        else:
            missing.append(f"{cat}: {key} → pildid/{image_filename(row)}")
        if cat not in decks:
            decks[cat] = genanki.Deck(int(hashlib.md5(cat.encode()).hexdigest()[:8], 16), f"Aednik 4. tase::{cat}")
        note = make_note(row, fname, meta.get(fname, {}).get("allikas", ""), model)
        if not note.cards:
            raise ValueError(f"Kirjest {row['id']} ei tekkinud ühtegi kaarti")
        decks[cat].add_note(note)
        card_count += len(note.cards)
        fallback_count += bool(note.fields[5])

    pkg = genanki.Package(list(decks.values()))
    pkg.media_files = sorted(media)
    out = HERE / "aednik_4.apkg"
    pkg.write_to_file(str(out))
    print(f"\nValmis: {out} ({len(rows)} kirjet, {card_count} kaarti, "
          f"{len(rows) - len(missing)} pildiga, {fallback_count} varukaarti, 0 kaartideta kirjet)")
    if missing:
        print("Pildita (lisa käsitsi pildid/ kausta või Ankis):")
        for item in missing:
            print("  -", item)


if __name__ == "__main__":
    main()
