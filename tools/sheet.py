"""Print sheet: a QR code to the songbook.

    python3 tools/sheet.py --out songbook-sheet.pdf
    python3 tools/sheet.py --wifi-name "Guest" --wifi-password secret
    python3 tools/sheet.py --mono --out songbook-sheet-bw.pdf   # for a black-and-white printer

Page 1 is an A4 poster for the wall or the host's desk, with what the site
does listed big under the QR code (the song count comes from songbook.json);
page 2 is four A6 table cards to cut out, with three of those features. With --wifi-name, both pages also carry a QR code that
joins the venue's Wi-Fi. The PDF can carry the Wi-Fi password, so
keep it out of the repo.
"""
import argparse
import json
import re
import sys
from pathlib import Path

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


def use_mono():
    """Black, white and neutral greys only: the pink and the purple-tinted greys turn
    into dithered tints on a black-and-white printer."""
    global INK, DIM, FAINT, ACCENT, BOX
    INK, DIM, FAINT, ACCENT, BOX = (HexColor(h) for h in ("#000000", "#444444", "#777777", "#000000", "#EDEDED"))


def qr(c, x, y, size, url, level="Q"):
    w = QrCodeWidget(url, barLevel=level, barWidth=size, barHeight=size, barBorder=2)
    w.barFillColor = INK
    d = Drawing(size, size)
    d.add(w)
    renderPDF.draw(d, c, x, y)


def centred(c, text, y, font, size, colour=None, cx=A4[0] / 2, spacing=0):
    c.setFont(font, size)
    c.setFillColor(colour or INK)
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


def centred_parts(c, parts, y, cx=A4[0] / 2):
    """One centred line made of (text, font, size, colour) runs, sharing a baseline."""
    width = sum(c.stringWidth(t, f, sz) for t, f, sz, _ in parts)
    x = cx - width / 2
    for t, f, sz, col in parts:
        text(c, x, y, t, f, sz, col)
        x += c.stringWidth(t, f, sz)


def url_line(c, url, y, size, cx=A4[0] / 2):
    centred_parts(c, [("Can't scan it? Go to ", "Helvetica", size * 0.7, DIM),
                      (short(url), "Helvetica-Bold", size, INK)], y, cx)


def short(url):
    return re.sub(r"^https?://", "", url).rstrip("/")


def wifi_payload(name, password):
    """The string phone cameras read as "join this network"."""
    esc = lambda v: re.sub(r'([\\;,:"])', r"\\\1", v)
    if not password:
        return f"WIFI:T:nopass;S:{esc(name)};;"
    return f"WIFI:T:WPA;S:{esc(name)};P:{esc(password)};;"


def text(c, x, y, s, font, size, colour=None):
    c.setFont(font, size)
    c.setFillColor(colour or INK)
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


SONGBOOK = Path(__file__).resolve().parent.parent / "songbook.json"


def song_count():
    """"18,000+" from the list itself, so the poster stays true as the list grows."""
    try:
        n = len(json.loads(SONGBOOK.read_text())["s"])
    except (OSError, ValueError, KeyError):
        return "every"
    return f"{n // 1000 * 1000:,}+" if n >= 2000 else f"{n:,}"


def features():
    return [
        ("search", f"Search {song_count()} songs", "By title or artist"),
        ("sliders", "Browse by genre & decade", "Or by male, female and duet"),
        ("heart", "Save your favourites", "Kept on your phone for next time"),
        ("sparkle", "Get songs picked for you", "Based on the ones you save"),
        ("play", "Listen before you sing", "On Spotify, Apple Music or YouTube"),
        ("calendar", "See our next karaoke nights", "Along the bottom of the page"),
    ]


def icon(c, kind, cx, cy, r):
    """A white pictogram in a pink disc of radius r, centred on (cx, cy)."""
    c.saveState()
    c.setFillColor(ACCENT)
    c.circle(cx, cy, r, stroke=0, fill=1)
    white = HexColor("#FFFFFF")
    c.setFillColor(white)
    c.setStrokeColor(white)
    c.setLineWidth(r * 0.14)
    c.setLineCap(1)
    c.setLineJoin(1)
    k = r
    if kind == "search":
        c.circle(cx - 0.12 * k, cy + 0.12 * k, 0.32 * k, stroke=1, fill=0)
        c.line(cx + 0.12 * k, cy - 0.12 * k, cx + 0.42 * k, cy - 0.42 * k)
    elif kind == "sliders":
        for dy, knob in ((0.32, -0.18), (0, 0.2), (-0.32, -0.05)):
            c.line(cx - 0.45 * k, cy + dy * k, cx + 0.45 * k, cy + dy * k)
            c.circle(cx + knob * k, cy + dy * k, 0.11 * k, stroke=0, fill=1)
    elif kind == "heart":
        p = c.beginPath()
        p.moveTo(cx, cy - 0.45 * k)
        p.curveTo(cx - 0.2 * k, cy - 0.28 * k, cx - 0.52 * k, cy - 0.05 * k, cx - 0.52 * k, cy + 0.17 * k)
        p.curveTo(cx - 0.52 * k, cy + 0.47 * k, cx - 0.12 * k, cy + 0.55 * k, cx, cy + 0.27 * k)
        p.curveTo(cx + 0.12 * k, cy + 0.55 * k, cx + 0.52 * k, cy + 0.47 * k, cx + 0.52 * k, cy + 0.17 * k)
        p.curveTo(cx + 0.52 * k, cy - 0.05 * k, cx + 0.2 * k, cy - 0.28 * k, cx, cy - 0.45 * k)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "sparkle":
        pts = [(0, 0.55), (0.14, 0.14), (0.55, 0), (0.14, -0.14), (0, -0.55), (-0.14, -0.14), (-0.55, 0), (-0.14, 0.14)]
        p = c.beginPath()
        p.moveTo(cx + pts[0][0] * k, cy + pts[0][1] * k)
        for x, y in pts[1:]:
            p.lineTo(cx + x * k, cy + y * k)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "play":
        p = c.beginPath()
        p.moveTo(cx - 0.18 * k, cy + 0.38 * k)
        p.lineTo(cx + 0.42 * k, cy)
        p.lineTo(cx - 0.18 * k, cy - 0.38 * k)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    elif kind == "calendar":
        c.roundRect(cx - 0.42 * k, cy - 0.38 * k, 0.84 * k, 0.72 * k, 0.1 * k, stroke=1, fill=0)
        c.line(cx - 0.42 * k, cy + 0.12 * k, cx + 0.42 * k, cy + 0.12 * k)
        c.line(cx - 0.2 * k, cy + 0.34 * k, cx - 0.2 * k, cy + 0.48 * k)
        c.line(cx + 0.2 * k, cy + 0.34 * k, cx + 0.2 * k, cy + 0.48 * k)
    c.restoreState()


def feature_list(c, x, top, items, size, gap, detail=True):
    """Icon, bold headline and a dim line under it, one per row, from top downwards."""
    r = size * 0.62
    for i, (kind, head, sub) in enumerate(items):
        y = top - i * gap
        icon(c, kind, x + r, y - r, r)
        tx = x + 2 * r + size * 0.55
        if detail:
            text(c, tx, y - r + size * 0.05, head, "Helvetica-Bold", size)
            text(c, tx, y - r - size * 0.78, sub, "Helvetica", size * 0.56, DIM)
        else:
            text(c, tx, y - r - size * 0.35, head, "Helvetica-Bold", size)


def block_width(c, items, size):
    """Width of the widest row, so the list can be centred on the page as a block."""
    r = size * 0.62
    widest = max(max(c.stringWidth(h, "Helvetica-Bold", size), c.stringWidth(s, "Helvetica", size * 0.56))
                 for _, h, s in items)
    return 2 * r + size * 0.55 + widest


def poster(c, url, name, wifi=None):
    W, H = A4
    cx = W / 2
    items = features()
    centred(c, name.upper(), H - 18 * mm, "Helvetica-Bold", 11, FAINT, spacing=3.2)
    c.setFillColor(ACCENT)
    c.rect(cx - 9 * mm, H - 22.5 * mm, 18 * mm, 1.1 * mm, stroke=0, fill=1)
    centred(c, "Find your song", H - 40 * mm, "Helvetica-Bold", 44)
    centred(c, "Scan with your phone camera", H - 50 * mm, "Helvetica", 15, DIM)

    if not wifi:
        size = 80 * mm
        qr(c, cx - size / 2, H - 56 * mm - size, size, url)
        fs = 23.5
        bw = block_width(c, items, fs)
        feature_list(c, cx - bw / 2, H - 143 * mm, items, fs, 18.5 * mm)
        url_line(c, url, 38 * mm, 19)
        centred(c, "Or just come up and ask", 25 * mm, "Helvetica-Bold", 24, ACCENT)
        centred(c, "Found your song? Show it to the host with your first name.", 12 * mm, "Helvetica", 11, FAINT)
        return

    # Room for the Wi-Fi panel: a smaller songbook QR, then the features as headlines in two columns.
    size = 74 * mm
    qr(c, cx - size / 2, H - 56 * mm - size, size, url)
    fs, half = 15, len(items) // 2
    left, right = items[:half], items[half:]
    lw = block_width(c, [(k, h, "") for k, h, _ in left], fs)
    rw = block_width(c, [(k, h, "") for k, h, _ in right], fs)
    gutter = 10 * mm
    x0 = cx - (lw + gutter + rw) / 2
    ftop = H - 56 * mm - size - 8 * mm
    feature_list(c, x0, ftop, left, fs, 12 * mm, detail=False)
    feature_list(c, x0 + lw + gutter, ftop, right, fs, 12 * mm, detail=False)
    url_line(c, url, ftop - half * 12 * mm - 6 * mm, 17)
    centred(c, "Or just come up and ask", ftop - half * 12 * mm - 17 * mm, "Helvetica-Bold", 20, ACCENT)

    box_x, box_y, box_w, box_h = 22 * mm, 22 * mm, W - 44 * mm, 44 * mm
    c.setFillColor(BOX)
    c.roundRect(box_x, box_y, box_w, box_h, 5 * mm, stroke=0, fill=1)
    wifi_block(c, box_x + 6 * mm, box_y + 6 * mm, 32 * mm, wifi)
    centred(c, "Found your song? Show it to the host with your first name.", 12 * mm, "Helvetica", 11, FAINT)


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
                size = 56 * mm
                qr(c, cx - size / 2, y0 + ch - 35 * mm - size, size, url)
                few = [features()[i] for i in (0, 2, 4)]
                bw = block_width(c, [(k, h, "") for k, h, _ in few], 10.5)
                feature_list(c, cx - bw / 2, y0 + 45 * mm, few, 10.5, 8 * mm, detail=False)
                centred(c, short(url), y0 + 10 * mm, "Helvetica-Bold", 12, cx=cx)
                continue
            centred(c, name.upper(), y0 + ch - 11 * mm, "Helvetica-Bold", 8, FAINT, cx=cx, spacing=2.2)
            centred(c, "Find your song", y0 + ch - 20 * mm, "Helvetica-Bold", 19, cx=cx)
            centred(c, "Scan with your phone camera", y0 + ch - 26.5 * mm, "Helvetica", 10, DIM, cx=cx)
            size = 48 * mm
            qr(c, cx - size / 2, y0 + ch - 30 * mm - size, size, url)
            centred(c, short(url), y0 + 45 * mm, "Helvetica-Bold", 11, cx=cx)
            c.setFillColor(BOX)
            c.roundRect(x0 + 7 * mm, y0 + 7 * mm, cw - 14 * mm, 33 * mm, 3 * mm, stroke=0, fill=1)
            wifi_block(c, x0 + 10 * mm, y0 + 10 * mm, 27 * mm, wifi, scale=0.62)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--wifi-name", help="venue Wi-Fi network to add a join-the-Wi-Fi QR")
    ap.add_argument("--wifi-password", help="leave out for an open network")
    ap.add_argument("--mono", action="store_true", help="black and white only, for a mono printer")
    ap.add_argument("--out", default="songbook-sheet.pdf")
    args = ap.parse_args()
    if args.mono:
        use_mono()
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
