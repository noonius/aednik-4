#!/usr/bin/env python3
"""Loob 4 A6 kaardiga A4 lehed. Kahepoolne trükk: piki pikka serva, 100%."""
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'output/pdf/Aednik-4-opikaardid-A6.pdf'
WIDTH, HEIGHT = A4
CARD_W, CARD_H = 105 * mm, 148 * mm
BOTTOM = (HEIGHT - 2 * CARD_H) / 2
INK = colors.HexColor('#244b37')
MUTED = colors.HexColor('#626963')


def load_plants():
    source = (ROOT / 'docs/taimed.js').read_text(encoding='utf-8')
    prefix = 'window.PLANTS = '
    if not source.startswith(prefix):
        raise ValueError('Veebiandmete vorming ei sobi')
    plants = json.loads(source[len(prefix):].strip().removesuffix(';'))
    if not plants or len({p['id'] for p in plants}) != len(plants):
        raise ValueError('Tühi õpinimekiri või korduvad ID-d')
    for plant in plants:
        if not (plant['estonian'] or plant['latin']):
            raise ValueError(f"Kirjel puudub nimi: {plant['id']}")
        if plant['image'] and not (ROOT / 'docs' / plant['image']).is_file():
            raise ValueError(f"Puuduv pilt: {plant['image']}")
    return plants


def back_order(cards):
    """Vaade tagant: vasak ja parem veerg vahetuvad, read jäävad samaks."""
    assert len(cards) == 4
    return [cards[1], cards[0], cards[3], cards[2]]


def paragraph(pdf, text, x, y, width, height, size=18, font='Card', color=INK,
              align=TA_CENTER):
    """Mahuta kogu tekst etteantud kasti, ka pildiallikate pikad omistused."""
    for step in range(31):
        actual = size - step * 0.25
        style = ParagraphStyle('card', fontName=font, fontSize=actual,
                               leading=actual * 1.3, textColor=color,
                               alignment=align, splitLongWords=True)
        glyphs = pdfmetrics.getFont(font).face.charWidths
        markup = ''.join(escape(char) if ord(char) in glyphs else
                         f'<font name="CardUnicode">{escape(char)}</font>'
                         for char in text)
        p = Paragraph(markup, style)
        _, needed = p.wrap(width, height)
        if needed <= height:
            p.drawOn(pdf, x, y + (height - needed) / 2)
            return
    raise ValueError(f'Tekst ei mahu kaardile: {text}')


def draw_card(pdf, slot, numbered, back=False):
    if numbered is None:
        return
    number, plant = numbered
    col, row = slot % 2, slot // 2
    pdf.saveState()
    pdf.translate(col * CARD_W, BOTTOM + (1 - row) * CARD_H)
    pad, usable = 8 * mm, CARD_W - 16 * mm
    pdf.setFillColor(MUTED)
    pdf.setFont('Card', 7)
    pdf.drawString(pad, 7 * mm, 'Aednik 4')
    pdf.drawRightString(CARD_W - pad, 7 * mm, f'{number:03d}')
    fallback = not plant['image'] and not (plant['estonian'] and plant['latin'])
    heading = plant['group'] if not fallback or back else 'Õpinimekirja rühmad'
    paragraph(pdf, heading, pad, 133 * mm, usable, 7 * mm,
              size=9, font='CardBold', color=MUTED)
    if back:
        paragraph(pdf, 'VASTUS', pad, 113 * mm, usable, 6 * mm,
                  size=8, color=MUTED)
        paragraph(pdf, plant['estonian'] or 'Eestikeelne nimi puudub',
                  pad, 81 * mm, usable, 29 * mm, size=22, font='CardBold')
        paragraph(pdf, plant['latin'] or 'Ladinakeelne nimi puudub',
                  pad, 56 * mm, usable, 23 * mm, size=18, font='CardItalic')
        if fallback:
            paragraph(pdf, plant['group'], pad, 39 * mm, usable, 15 * mm, size=15)
        if plant['source']:
            paragraph(pdf, 'Foto: ' + plant['source'], pad, 15 * mm,
                      usable, 17 * mm, size=7, color=MUTED, align=TA_LEFT)
    elif plant['image']:
        pdf.drawImage(str(ROOT / 'docs' / plant['image']), pad, 32 * mm,
                      width=usable, height=96 * mm,
                      preserveAspectRatio=True, anchor='c')
        paragraph(pdf, 'Mis on pildil?', pad, 17 * mm, usable, 10 * mm, size=16)
    else:
        paragraph(pdf, plant['estonian'] or plant['latin'],
                  pad, 66 * mm, usable, 47 * mm, size=22, font='CardBold')
        question = ('Millisesse õpinimekirja rühma see kuulub?' if fallback
                    else 'Mis on ladinakeelne nimi?')
        paragraph(pdf, question, pad, 39 * mm, usable, 20 * mm, size=15)
    pdf.restoreState()


def cut_lines(pdf):
    pdf.saveState()
    pdf.setStrokeColor(colors.HexColor('#aeb4ae'))
    pdf.setLineWidth(0.25)
    pdf.setDash(2, 3)
    pdf.line(CARD_W, BOTTOM, CARD_W, BOTTOM + 2 * CARD_H)
    # A4 kõrgus 297 mm, kaks A6 kaarti kokku 296 mm.
    for y in [BOTTOM, BOTTOM + CARD_H, BOTTOM + 2 * CARD_H]:
        pdf.line(0, y, WIDTH, y)
    pdf.restoreState()


def main():
    fonts = Path(reportlab.__file__).parent / 'fonts'
    for name, file in [('Card', 'Vera.ttf'), ('CardBold', 'VeraBd.ttf'),
                       ('CardItalic', 'VeraIt.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    plants = load_plants()
    # Fotograafide nimed sisaldavad ka kirillitsat, kreeka ja jaapani kirja.
    chars = set(''.join(p[key] for p in plants
                        for key in ['estonian', 'latin', 'group', 'source']))
    missing = {ord(char) for char in chars
               if ord(char) not in pdfmetrics.getFont('Card').face.charWidths}
    candidates = [os.environ.get('AEDNIK_PDF_FONT', ''),
                  '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for path in candidates:
        if path and Path(path).is_file():
            fallback = TTFont('CardUnicode', path)
            if missing <= fallback.face.charWidths.keys():
                pdfmetrics.registerFont(fallback)
                break
    else:
        if missing:
            raise ValueError('Omistuste jaoks on vaja Unicode TTF-fonti. '
                             'Määra selle asukoht muutujaga AEDNIK_PDF_FONT.')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
    pdf.setTitle('Aednik 4 - A6 õpikaardid')
    pdf.setAuthor('Aednik 4')
    pdf.setSubject('A4; 4 A6 kaarti; kahepoolne trükk piki pikka serva; 100%')
    pdf.setViewerPreference('Duplex', 'DuplexFlipLongEdge')
    pdf.setViewerPreference('PrintScaling', 'None')
    numbered = list(enumerate(plants, 1))
    for offset in range(0, len(numbered), 4):
        cards = numbered[offset:offset + 4]
        cards += [None] * (4 - len(cards))
        for back, side in [(False, cards), (True, back_order(cards))]:
            for slot, card in enumerate(side):
                draw_card(pdf, slot, card, back=back)
            cut_lines(pdf)
            pdf.showPage()
    pdf.save()
    sheets = (len(plants) + 3) // 4
    print(f'{len(plants)} kaarti, {sheets} A4 lehte, {sheets * 2} PDF-lehekülge: {OUTPUT}')


if __name__ == '__main__':
    main()
