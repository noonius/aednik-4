"""Pakib õppimistööriista koos fotodega ühte offline HTML-faili."""
import base64
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "docs"
page = (DIST / "index.html").read_text()
page = re.sub(r'  <script src="[^"]+" defer></script>\n', '', page)
page = page.replace('<link rel="stylesheet" href="style.css">', '<style>' + (DIST / "style.css").read_text() + '</style>')
page = page.replace('<link rel="manifest" href="manifest.webmanifest">', '')
icon = 'data:image/svg+xml;base64,' + base64.b64encode((DIST / 'icon.svg').read_bytes()).decode()
page = page.replace('href="icon.svg"', 'href="' + icon + '"')
data = "window.STANDALONE = true;\n" + (DIST / "taimed.js").read_text()
for picture in (DIST / "pildid").glob("*.jpg"):
    uri = 'data:image/jpeg;base64,' + base64.b64encode(picture.read_bytes()).decode()
    data = data.replace('"pildid/' + picture.name + '"', '"' + uri + '"')
scripts = [data, (DIST / "study.js").read_text(), (DIST / "app.js").read_text()]
page = page.replace('</body>', '\n'.join('<script>' + script.replace('</script', '<\\/script') + '</script>' for script in scripts) + '\n</body>')
output = ROOT / "Aednik 4.html"
output.write_text(page)
assert 'src="app.js"' not in page and '"pildid/' not in page
print(f"Valmis: {output.name} ({output.stat().st_size / 1e6:.1f} MB)")
