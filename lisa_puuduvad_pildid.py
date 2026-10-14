#!/usr/bin/env python3
"""Laadib eraldi veebiuuringus leitud fotod pildiallikad.json failist.

Käivita: .venv/bin/python lisa_puuduvad_pildid.py
Seejärel uuenda Anki pakki: .venv/bin/python tee_pakk.py
Olemasolevaid terveid pilte ei asendata. Ebaselge vaste jäetakse laadimata.
Commonsi suurte originaalide asemel kasutatakse API pakutud pisipilte.
Päringute vahel on paus; HTTP 429 peatab laadimise. Hilisem korduskäivitus
jätab juba salvestatud pildid vahele.
"""
import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse

import tee_pakk as pakk

REQUEST_PAUSE = 2


def image_url(source):
    url = source["pildi_url"]
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname != "upload.wikimedia.org" or not parsed.path.startswith("/wikipedia/commons/"):
        return url
    parts = parsed.path.split("/")
    filename = urllib.parse.unquote(parts[-2] if "/commons/thumb/" in parsed.path else parts[-1])
    params = {"action": "query", "format": "json", "formatversion": 2,
              "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": 960,
              "titles": "File:" + filename}
    data = pakk.get_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    for page in data.get("query", {}).get("pages", []):
        for info in page.get("imageinfo", []):
            if info.get("thumburl"):
                return info["thumburl"]
            # Väikese originaali jaoks pole vaja üles suurendatud pisipilti.
            if 0 < info.get("width", 0) <= 960 and info.get("url"):
                return info["url"]
    raise ValueError(f"Commonsi API ei andnud pildilinki: {filename}")


def read_sources(path):
    rows = {row["id"]: row for row in pakk.read_rows(pakk.HERE / "taimed.csv")}
    with open(path, encoding="utf-8") as stream:
        sources = json.load(stream)
    seen = set()
    for source in sources:
        row = rows.get(source["id"])
        if row is None or source["id"] in seen or source["fail"] != pakk.image_filename(row):
            raise ValueError(f"Pildiallika ID või failinimi ei sobi CSV-ga: {source['nimi']}")
        seen.add(source["id"])
        if source.get("kindel") is True:
            for field in ["pildi_url", "allika_url"]:
                parsed = urllib.parse.urlparse(source.get(field, ""))
                if parsed.scheme != "https" or not parsed.hostname:
                    raise ValueError(f"Puudub sobiv {field}: {source['nimi']}")
            if not source.get("allikas"):
                raise ValueError(f"Puudub pildi omistus: {source['nimi']}")
    return sources


def add_images(sources, meta):
    downloaded = failed = 0
    for source in sources:
        if source.get("kindel") is not True:
            print(f"Jäetud ootele: {source['nimi']} ({source.get('markus', 'ebaselge vaste')})")
            continue
        path = pakk.IMG_DIR / source["fail"]
        if pakk.valid_image(path):
            print(f"Pilt on olemas: {source['nimi']}")
            continue
        print(f"Laadin: {source['nimi']}", flush=True)
        try:
            time.sleep(REQUEST_PAUSE)
            url = image_url(source)
            if url != source["pildi_url"] or urllib.parse.urlparse(url).hostname == "upload.wikimedia.org":
                time.sleep(REQUEST_PAUSE)
            pakk.download(url, path)
        except (OSError, ValueError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                print("  Server piiras päringuid (HTTP 429). Peatasin laadimise; salvestatud pildid jäävad alles.")
                retry = (error.headers or {}).get("Retry-After")
                print(f"  Retry-After: {retry}" if retry else "  Proovi hiljem uuesti; praegu rohkem päringuid ei saadeta.")
                failed += 1
                break
            # DNS-i puudumisel ei ole mõtet kõiki ülejäänud allikaid läbi proovida.
            if isinstance(error, urllib.error.URLError) and isinstance(error.reason, socket.gaierror):
                raise RuntimeError("Veebiaadresse ei saa lahendada. Käivita võrguühendusega terminalis.") from error
            print(f"  Laadimine ebaõnnestus: {error}")
            failed += 1
            continue
        credit = source["allikas"]
        if source.get("litsents"):
            credit += "; " + source["litsents"]
        credit += "; " + source["allika_url"] + "; JPEG-vormingusse teisendatud"
        if source.get("markus"):
            credit += "; " + source["markus"]
        meta[source["fail"]] = {
            "nimi": source["nimi"],
            "käsitsi": True,
            "url": url,
            "algne_url": source["pildi_url"],
            "allika_url": source["allika_url"],
            "allikas": credit,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        pakk.save_meta(meta)
        downloaded += 1
    return downloaded, failed


def main():
    sources = read_sources(pakk.HERE / "pildiallikad.json")
    pakk.IMG_DIR.mkdir(exist_ok=True)
    meta = {}
    if pakk.META.exists():
        with pakk.META.open(encoding="utf-8") as stream:
            meta = json.load(stream)
    downloaded, failed = add_images(sources, meta)
    rows = pakk.read_rows(pakk.HERE / "taimed.csv")
    missing = sum(not pakk.valid_image(pakk.IMG_DIR / pakk.image_filename(row)) for row in rows)
    print(f"\nLisatud {downloaded} pilti, {failed} laadimisviga, {missing} kirjet veel pildita.")
    print("Paki uuendamiseks käivita .venv/bin/python tee_pakk.py")


if __name__ == "__main__":
    main()
