"""Print sheet: a QR code to the songbook.

    python3 tools/sheet.py --out songbook-sheet.pdf
    python3 tools/sheet.py --wifi-name "Guest" --wifi-password secret

Page 1 is an A4 poster for the wall or the host's desk; page 2 is four A6
table cards to cut out. With --wifi-name, both pages also carry a QR code that
joins the venue's Wi-Fi. The PDF can carry the Wi-Fi password, so
keep it out of the repo.
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

URL = "https://maddogkaraoke.co.uk/"
NAME = "Mad Dog Karaoke"
INK = HexColor("#150C24")
DIM = HexColor("#5E5470")
FAINT = HexColor("#9B8FB0")
ACCENT = HexColor("#ED1F61")
BOX = HexColor("#F3F0F7")


def qr(c, x, y, size, url, level="Q"):
    w = QrCodeWidget(url, barLevel=level, barWidth=size, barHeight=size, barBorder=2)
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


def short(url):
    return re.sub(r"^https?://", "", url).rstrip("/")


def wifi_payload(name, password):
    """The string phone cameras read as "join this network"."""
    esc = lambda v: re.sub(r'([\\;,:"])', r"\\\1", v)
    if not password:
        return f"WIFI:T:nopass;S:{esc(name)};;"
    return f"WIFI:T:WPA;S:{esc(name)};P:{esc(password)};;"


def text(c, x, y, s, font, size, colour=INK):
    c.setFont(font, size)
    c.setFillColor(colour)
    c.drawString(x, y, s)


def wifi_block(c, x, y, qr_size, wifi, scale=1.0):
    """Wi-Fi QR on the left, network and password beside it, bottom-left at (x, y)."""
    name, password = wifi
    qr(c, x, y, qr_size, wifi_payload(name, password), level="M")
    tx = x + qr_size + 6 * mm * scale
    top = y + qr_size - 7 * mm * scale
    text(c, tx, top, "Free Wi-Fi", "Helvetica-Bold", 15 * scale)
    text(c, tx, top - 6.5 * mm * scale, "Scan to join, or pick the network:", "Helvetica", 10.5 * scale, DIM)
    rows = [("Network", name)] + ([("Password", password)] if password else [])
    for i, (label, value) in enumerate(rows):
        ry = top - (14.5 + 7 * i) * mm * scale
        text(c, tx, ry, label, "Helvetica", 10.5 * scale, DIM)
        text(c, tx + 21 * mm * scale, ry, value, "Helvetica-Bold", 13 * scale)


def poster(c, url, name, wifi=None):
    W, H = A4
    cx = W / 2
    centred(c, name.upper(), H - 30 * mm, "Helvetica-Bold", 11, FAINT, spacing=3.2)
    c.setFillColor(ACCENT)
    c.rect(cx - 9 * mm, H - 35 * mm, 18 * mm, 1.1 * mm, stroke=0, fill=1)
    centred(c, "Find your song", H - 56 * mm, "Helvetica-Bold", 46)
    centred(c, "Scan with your phone camera to see every song we've got.", H - 68 * mm, "Helvetica", 14, DIM)
    centred(c, "Search by title or artist, or browse by genre and decade.", H - 75 * mm, "Helvetica", 14, DIM)

    if not wifi:
        size = 104 * mm
        qr(c, cx - size / 2, H - 87 * mm - size, size, url)
        top = H - 87 * mm - size - 14 * mm
        centred(c, "Can't scan it? Type this into your browser:", 34 * mm, "Helvetica", 11, DIM)
        centred(c, short(url), 27 * mm, "Helvetica-Bold", 12.5)
        centred(c, "Found your song? Let the host know.", 15 * mm, "Helvetica", 11, FAINT)
        return

    # Room for the Wi-Fi panel: a smaller songbook QR, the fallback URL on one line.
    size = 88 * mm
    qr(c, cx - size / 2, H - 86 * mm - size, size, url)
    top = H - 86 * mm - size - 11 * mm
    centred(c, f"Can't scan it? Go to {short(url)}", top - 41 * mm, "Helvetica", 11, DIM)

    box_x, box_y, box_w, box_h = 22 * mm, 22 * mm, W - 44 * mm, 44 * mm
    c.setFillColor(BOX)
    c.roundRect(box_x, box_y, box_w, box_h, 5 * mm, stroke=0, fill=1)
    wifi_block(c, box_x + 6 * mm, box_y + 6 * mm, 32 * mm, wifi)
    centred(c, "Found your song? Let the host know.", 12 * mm, "Helvetica", 11, FAINT)


def cards(c, url, name, wifi=None):
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
            if not wifi:
                centred(c, name.upper(), y0 + ch - 14 * mm, "Helvetica-Bold", 8, FAINT, cx=cx, spacing=2.2)
                centred(c, "Find your song", y0 + ch - 24 * mm, "Helvetica-Bold", 21, cx=cx)
                centred(c, "Scan with your phone camera", y0 + ch - 31 * mm, "Helvetica", 10.5, DIM, cx=cx)
                size = 62 * mm
                qr(c, cx - size / 2, y0 + ch - 35 * mm - size, size, url)
                centred(c, short(url), y0 + 12 * mm, "Helvetica", 8.5, DIM, cx=cx)
                continue
            centred(c, name.upper(), y0 + ch - 11 * mm, "Helvetica-Bold", 8, FAINT, cx=cx, spacing=2.2)
            centred(c, "Find your song", y0 + ch - 20 * mm, "Helvetica-Bold", 19, cx=cx)
            centred(c, "Scan with your phone camera", y0 + ch - 26.5 * mm, "Helvetica", 10, DIM, cx=cx)
            size = 48 * mm
            qr(c, cx - size / 2, y0 + ch - 30 * mm - size, size, url)
            centred(c, short(url), y0 + 46 * mm, "Helvetica", 8.5, DIM, cx=cx)
            c.setFillColor(BOX)
            c.roundRect(x0 + 7 * mm, y0 + 7 * mm, cw - 14 * mm, 33 * mm, 3 * mm, stroke=0, fill=1)
            wifi_block(c, x0 + 10 * mm, y0 + 10 * mm, 27 * mm, wifi, scale=0.62)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--wifi-name", help="venue Wi-Fi network to add a join-the-Wi-Fi QR")
    ap.add_argument("--wifi-password", help="leave out for an open network")
    ap.add_argument("--out", default="songbook-sheet.pdf")
    args = ap.parse_args()
    wifi = (args.wifi_name, args.wifi_password) if args.wifi_name else None
    c = canvas.Canvas(args.out, pagesize=A4)
    c.setTitle(f"{args.name} songbook - scan to browse")
    c.setAuthor(args.name)
    poster(c, args.url, args.name, wifi)
    c.showPage()
    cards(c, args.url, args.name, wifi)
    c.showPage()
    c.save()
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
