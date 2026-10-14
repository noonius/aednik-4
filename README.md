# Aednik 4

Aedniku 4. taseme õppematerjal: Anki kaardipakk ja veebirakendus taimede, kahjustajate ning haiguste õppimiseks. Õpinimekirjas on 419 kirjet 14 rühmas.

## Õppimine

- [Anki kaardipakk](aednik_4.apkg). Ava fail GitHubis, vali **Download raw file** ning impordi allalaaditud pakk Ankisse.
- [Ühe failina veebirakendus](Aednik%204.html). Laadi alla ja ava brauseris. Pildid on failis kaasas ning internetti pole vaja.
- [Trükitavad A6 õpikaardid](output/pdf/Aednik-4-opikaardid-A6.pdf). 419 kaarti, neli kaarti A4 lehel; pildid või küsimused ees ja vastused taga.
- GitHub Pagesi veebilehe aadress on pärast avaldamist `https://noonius.github.io/aednik-4/`.

Veebirakendus salvestab õpiedu brauserisse. Õpiedu saab eksportida ja teise seadmesse importida. Telefonis saab avaldatud lehe avakuvale lisada ning materjali offline-kasutuseks alla laadida. [Veebirakenduse kasutamine ja piirangud](docs/README.md).

## Failid

| Fail või kaust | Sisu |
| --- | --- |
| `aednik_4.apkg` | Valmis Anki kaardipakk |
| `Aednik 4.html` | Iseseisev veebirakendus koos piltidega |
| `docs/` | GitHub Pagesi veebirakendus, selle lähtekood ja veebipildid |
| `taimed.csv` | Õpinimekiri püsivate kirjete ID-dega |
| `pildid/` | Anki paki lähtepildid ja fotode omistused |
| `tee_pakk.py` | Loob CSV ja piltide põhjal Anki paki |
| `lisa_puuduvad_pildid.py` | Laadib kinnitatud pildiallikatest puuduvaid pilte |
| `build_data.py` | Loob CSV ja Anki paki põhjal veebirakenduse andmed ning pildid |
| `build_standalone.py` | Koondab veebirakenduse ühte HTML-faili |
| `tee_pdf.py` | Loob kahepoolseks trükiks A6 õpikaardid A4 lehtedel |
| `output/pdf/` | Valmis trükitav õpikaartide PDF |
| `pildiallikad.json`, `puuduvad_*.json` | Pildiallikate ja puuduva materjali andmed |

## GitHub Pages

Laadi kogu see kataloog GitHubi avalikku repositooriumi nimega `aednik-4`. Kohalik virtuaalkeskkond ja tööriistade seaded on `.gitignore` failiga välistatud.

Loo GitHubis tühi avalik repo `aednik-4`, seejärel käivita selle kataloogi terminalis.:

```sh
git init -b main
git add .
git commit -m "Lisa Aednik 4 õppematerjalid ja veebirakendus"
git remote add origin git@github.com:noonius/aednik-4.git
git push -u origin main
```

1. Ava repositooriumi **Settings → Pages**.
2. Vali **Source → Deploy from a branch**.
3. Vali haru **main**, kaust **/docs** ja vajuta **Save**.
4. Oota avaldamise lõppu. Lehe link ilmub samale seadete lehele.

Eraldi ehitussammu ega GitHub Actionsi töövoogu pole vaja. `docs/` sisaldab avaldamisvalmis faile ja `.nojekyll` keelab Jekylli töötluse. Suhtelised failiteed võimaldavad lehel töötada repo alamteel `/aednik-4/`. Anki pakk ja skriptid on kättesaadavad samast repositooriumist.

Muudatuste avaldamiseks uuenda vajalikud failid, tee commit ning push harusse `main`. Veebilehe uuendamisel peavad commit'is olema ka muutunud `docs/` failid.

## Kohalik kasutamine ja uuendamine

Käivita käsud repositooriumi juurkaustast. Vaja on Python 3.10 või uuemat; kontrollide jaoks ka Node.js-i.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Materjali uuendamine:

```sh
# Vajadusel laadi kinnitatud allikatest puuduvad pildid.
.venv/bin/python lisa_puuduvad_pildid.py

# Loo Anki pakk, seejärel veebiandmed ja ühefaililine versioon.
.venv/bin/python tee_pakk.py
.venv/bin/python build_data.py
.venv/bin/python build_standalone.py
```

Piltide allalaadimine ja Anki paki loomine võivad teha võrgupäringuid. Nime või kategooria parandamisel säilita `taimed.csv` kirje ID. Nii jääb Anki märkme identiteet samaks.

Veebiversiooni proovimine:

```sh
python3 -m http.server 8000 --directory docs
```

Ava `http://localhost:8000`. Offline-funktsioon töötab localhost-is või HTTPS-is.

## Õpikaartide trükkimine

PDF sisaldab 210 lehekülge ehk 105 kahepoolset A4 paberilehte. Iga õpinimekirja kirje kohta on üks kaart. Pildiga kaardi esiküljel on foto, tagaküljel nimed ja foto omistus. Pildita kirjel on ees eestikeelne nimi ning küsimus ladinakeelse nime kohta. Kui nimepaar puudub, küsib kaart õpinimekirja rühma.

1. Vali paber **A4**, püstpaigutus ning **tegelik suurus / 100%**. Ära kasuta lehele mahutamist ega printeri valikut „mitu lehekülge lehel”. Neli kaarti on juba PDF-i lehele paigutatud.
2. Lülita sisse kahepoolne trükk ja **pööra piki pikka serva**.
3. Prindi esmalt prooviks ainult PDF-i leheküljed **1-2** ühele paberile. Kontrolli vastu valgust, et mõlemal poolel on samas kohas sama kaardinumber ja lõikejooned kattuvad.
4. Sobiva tulemuse korral prindi kogu fail ja lõika piki punktiirjooni. Viimasel lehel on üks tühi kaardikoht.

Kaardid on 105 × 148 mm. A4 lehe poolitamisel saad kõrguseks 148,5 mm; täpse A6 saamiseks eemalda lisaks ülemisest ja alumisest välisservast 0,5 mm. Nende servade abijooned võivad jääda printeri prindialast välja. Kaartide sisu on servadest vähemalt 7 mm kaugusel. Printeri enda kahepoolse trüki nihke korral reguleeri printeri joondust.

PDF-i uuesti loomiseks pärast veebiandmete uuendamist:

```sh
.venv/bin/python tee_pdf.py
.venv/bin/python -m unittest test_tee_pdf
```

Skript kasutab ReportLabi kaasasolevaid fonte. Fotograafide eri kirjasüsteemides nimede jaoks kasutab see macOS-is Arial Unicode fonti. Teistes süsteemides määra vajadusel keskkonnamuutujaga `AEDNIK_PDF_FONT` kõiki omistustes esinevaid tähti toetava TTF-fondi asukoht. Kasutatud fondid manustatakse PDF-i; printijal pole neid vaja paigaldada.

## Kontrollid

```sh
.venv/bin/python -m unittest test_tee_pakk test_lisa_puuduvad_pildid
node test_study.cjs
node test_app.cjs
```

## Pildiallikad

Fotode omistused on failis [pildid/_allikad.json](pildid/_allikad.json), Anki kaartidel ja veebirakenduses vastuse juures. Täiendavad allikad on failis [pildiallikad.json](pildiallikad.json). Fotode kasutamisel järgi iga allika litsentsi ja omistustingimusi.

`pildid/_allikad.json` seob pildifaili nime algse pildi URL-i ja autori või litsentsi omistusega. Täiendatud kirjetel on ka `allika_url`, kontrolliinfo ja faili SHA-256 räsi. Fail sisaldab ka varasemate piltide kirjeid; veebis praegu kasutatava pildi leiab `docs/taimed.js` välja `image` kaudu. Kõigil praeguse veebiversiooni 367 pildil on `source` omistus. Veebivaates kuvatakse omistus tekstina; algallika URL on allikafailides.

## Mida Gitist välja jätame

`.gitignore` välistab virtuaalkeskkonna, Pythoni ja testide vahemälud, kohalikud tööriistaseaded, `.env` saladused, ajutised failid ning eksporditud `aednik-opiedu*.json` õpiedu varukoopiad. Algne õpinimekirja PDF ja uuringute Markdown-failid (`caliche-cards-uuring.md`, `pildiallikad.md`, `puuduvad_*.md`) jäävad samuti ainult kohalikku kausta.

Anki pakk, ühefaililine HTML, `docs/` veebiversioon, lähtepildid ja allikakirjed jäävad repositooriumi. Pakk ja HTML on küll genereeritud failid, kuid selles repos on need ka allalaaditavad õppematerjalid. `docs/` peab olema Gitis, et kirjeldatud GitHub Pagesi avaldamine töötaks.
