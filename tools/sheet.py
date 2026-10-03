"""Print sheet: a QR code to the songbook and the 6-digit code that opens it.

    python3 tools/sheet.py --code 123456 --out songbook-sheet.pdf

Page 1 is an A4 poster for the wall or the host's desk; page 2 is four A6
table cards to cut out. The PDF carries the code, so keep it out of the repo.
"""
import argparse
import re
import sys

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

URL = "https://surrealsucculents.github.io/karaoke-songbook/"
INK = HexColor("#150C24")
DIM = HexColor("#5E5470")
FAINT = HexColor("#9B8FB0")
ACCENT = HexColor("#ED1F61")
BOX = HexColor("#F3F0F7")


def qr(c, x, y, size, url):
    w = QrCodeWidget(url, barLevel="Q", barWidth=size, barHeight=size, barBorder=2)
    w.barFillColor = INK
    d = Drawing(size, size)
    d.add(w)
    renderPDF.draw(d, c, x, y)


def centred(c, text, y, font, size, colour=INK, cx=A4[0] / 2, spacing=0):
    c.setFont(font, size)
    c.setFillColor(colour)
    if spacing:
        width = sum(c.stringWidth(ch, font, size) for ch in text) + spacing * (len(text) - 1)
        c.saveState()  # character spacing would otherwise stick to every later line
        t = c.beginText(cx - width / 2, y)
        t.setFont(font, size)
        t.setCharSpace(spacing)
        t.textOut(text)
        c.drawText(t)
        c.restoreState()
    else:
        c.drawCentredString(cx, y, text)


def digits(c, code, cx, y, box_w, box_h, size, gap):
    """Six boxes, a wider gap after the third so it reads as two groups."""
    split = gap * 2.2
    total = 6 * box_w + 4 * gap + split
    x = cx - total / 2
    for i, d in enumerate(code):
        c.setFillColor(BOX)
        c.setStrokeColor(INK)
        c.setLineWidth(1.4)
        c.roundRect(x, y, box_w, box_h, box_w * 0.16, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", size)
        c.drawCentredString(x + box_w / 2, y + (box_h - size * 0.72) / 2, d)
        x += box_w + (split if i == 2 else gap)


def short(url):
    return re.sub(r"^https?://", "", url).rstrip("/")


def poster(c, code, url):
    W, H = A4
    cx = W / 2
    centred(c, "KARAOKE", H - 30 * mm, "Helvetica-Bold", 11, FAINT, spacing=3.2)
    c.setFillColor(ACCENT)
    c.rect(cx - 9 * mm, H - 35 * mm, 18 * mm, 1.1 * mm, stroke=0, fill=1)
    centred(c, "Find your song", H - 56 * mm, "Helvetica-Bold", 46)
    centred(c, "Scan with your phone camera to see every song we've got.", H - 68 * mm, "Helvetica", 14, DIM)
    centred(c, "Search by title or artist, or browse by genre and decade.", H - 75 * mm, "Helvetica", 14, DIM)

    size = 104 * mm
    qr(c, cx - size / 2, H - 87 * mm - size, size, url)

    top = H - 87 * mm - size - 14 * mm
    centred(c, "Then enter this code", top, "Helvetica-Bold", 15)
    digits(c, code, cx, top - 33 * mm, 21 * mm, 26 * mm, 44, 3.2 * mm)

    centred(c, "Can't scan it? Type this into your browser:", 34 * mm, "Helvetica", 11, DIM)
    centred(c, short(url), 27 * mm, "Helvetica-Bold", 12.5)
    centred(c, "Found your song? Let the host know.", 15 * mm, "Helvetica", 11, FAINT)


def cards(c, code, url):
    W, H = A4
    cw, ch = W / 2, H / 2
    c.setDash(3, 4)
    c.setStrokeColor(FAINT)
    c.setLineWidth(0.6)
    c.line(cw, 0, cw, H)
    c.line(0, ch, W, ch)
    c.setDash()
    for col in range(2):
        for row in range(2):
            x0, y0 = col * cw, row * ch
            cx = x0 + cw / 2
            centred(c, "KARAOKE", y0 + ch - 14 * mm, "Helvetica-Bold", 8, FAINT, cx=cx, spacing=2.2)
            centred(c, "Find your song", y0 + ch - 24 * mm, "Helvetica-Bold", 21, cx=cx)
            centred(c, "Scan, then enter the code", y0 + ch - 31 * mm, "Helvetica", 10.5, DIM, cx=cx)
            size = 62 * mm
            qr(c, cx - size / 2, y0 + ch - 35 * mm - size, size, url)
            digits(c, code, cx, y0 + 22 * mm, 11 * mm, 14 * mm, 23, 1.8 * mm)
            centred(c, short(url), y0 + 12 * mm, "Helvetica", 8.5, DIM, cx=cx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--out", default="songbook-sheet.pdf")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{6}", args.code):
        sys.exit("The code must be exactly 6 digits.")
    c = canvas.Canvas(args.out, pagesize=A4)
    c.setTitle("Karaoke songbook - scan to browse")
    c.setAuthor("Songbook")
    poster(c, args.code, args.url)
    c.showPage()
    cards(c, args.code, args.url)
    c.showPage()
    c.save()
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
