"""Lock the song list behind the 6-digit code, and keep it up to date.

The site only ever sees songbook.bin: the list gzipped, then encrypted with
AES-256-GCM under a key stretched from the code with PBKDF2-SHA256. Nobody gets
the list from the repo or the site without the code on the printed sheet.

    # First build, from a tagged list (title, artist, year, genre per song)
    python3 tools/build.py lock --code 123456 --songs songs.json

    # The KJ software exported a new list: re-clean it, keep every decade and
    # genre already known, re-lock with the same code
    python3 tools/build.py update --code 123456 --track Songlist-fulltrack.txt

    # New code (then reprint the sheet with tools/sheet.py)
    python3 tools/build.py rekey --old-code 123456 --code 654321

    # Get the plain list back out, to check or hand-edit it
    python3 tools/build.py unlock --code 123456 --out songs.json
"""
import argparse
import gzip
import json
import os
import re
import secrets
import struct
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

sys.path.insert(0, os.path.dirname(__file__))
import clean  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "songbook.bin")
MAGIC = b"SBK1"
ITERATIONS = 310_000

GENRES = ["Pop", "Rock", "Indie & Alternative", "Dance", "R&B & Soul", "Hip-Hop & Rap",
          "Country", "Musicals & Film", "Christmas", "Swing & Easy Listening",
          "Folk & Irish", "Reggae & Ska", "Latin", "Novelty & Kids"]


def check_code(code):
    if not re.fullmatch(r"\d{6}", code or ""):
        sys.exit("The code must be exactly 6 digits.")
    return code


def derive(code, salt, iterations):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(code.encode())


def sort_key(s):
    k = clean.fold(s)
    k = re.sub(r"[^a-z0-9 ]+", "", k).strip()
    return k


def artist_sort_key(s):
    return re.sub(r"^the ", "", sort_key(s))


# ---------------------------------------------------------------- payload

def pack(songs):
    """[{t, a, p, y, g}] -> compact JSON the page reads."""
    artists = sorted({s["p"] for s in songs}, key=lambda a: (artist_sort_key(a), a))
    index = {a: i for i, a in enumerate(artists)}
    rows = []
    for s in sorted(songs, key=lambda s: (sort_key(s["t"]), artist_sort_key(s["p"]))):
        g = GENRES.index(s["g"]) if s.get("g") in GENRES else -1
        row = [s["t"], index[s["p"]], int(s.get("y") or 0), g]
        if s["a"] != s["p"]:
            row.append(s["a"])
        rows.append(row)
    return {"v": 1, "g": GENRES, "a": artists, "s": rows}


def unpack(payload):
    artists, genres = payload["a"], payload["g"]
    songs = []
    for row in payload["s"]:
        t, ai, y, g = row[:4]
        p = artists[ai]
        songs.append({"t": t, "p": p, "a": row[4] if len(row) > 4 else p,
                      "y": y or None, "g": genres[g] if g >= 0 else None})
    return songs


def lock(songs, code):
    data = gzip.compress(json.dumps(pack(songs), ensure_ascii=False, separators=(",", ":")).encode(), 9)
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    sealed = AESGCM(derive(code, salt, ITERATIONS)).encrypt(iv, data, MAGIC)
    with open(BIN, "wb") as f:
        f.write(MAGIC + struct.pack(">I", ITERATIONS) + salt + iv + sealed)
    print(f"locked {len(songs)} songs into {os.path.relpath(BIN)} ({os.path.getsize(BIN) // 1024} KB)")


def unlock_bin(code):
    blob = open(BIN, "rb").read()
    if blob[:4] != MAGIC:
        sys.exit("songbook.bin is not a songbook file.")
    iterations = struct.unpack(">I", blob[4:8])[0]
    salt, iv, sealed = blob[8:24], blob[24:36], blob[36:]
    try:
        data = AESGCM(derive(code, salt, iterations)).decrypt(iv, sealed, MAGIC)
    except Exception:
        sys.exit("That code does not open songbook.bin.")
    return unpack(json.loads(gzip.decompress(data)))


# ---------------------------------------------------------------- commands

def cmd_lock(args):
    songs = json.load(open(args.songs))
    for s in songs:
        s.setdefault("a", s["p"])
    lock(songs, check_code(args.code))


def cmd_unlock(args):
    songs = unlock_bin(check_code(args.code))
    json.dump(songs, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {len(songs)} songs to {args.out}")


def cmd_rekey(args):
    lock(unlock_bin(check_code(args.old_code)), check_code(args.code))


def cmd_update(args):
    code = check_code(args.code)
    known = {}
    for s in unlock_bin(code):
        known[(clean.title_key(s["t"]), clean.key(s["p"]))] = s
    fresh = clean.clean(clean.load(args.track, args.artist))
    songs, missing = [], 0
    for s in fresh:
        old = known.get((clean.title_key(s["t"]), clean.key(s["p"]))) or known.get((s["tk"], clean.key(s["p"])))
        y, g = (old["y"], old["g"]) if old else (None, None)
        missing += old is None
        songs.append({"t": s["t"], "a": s["a"], "p": s["p"], "y": y, "g": g})
    print(f"{len(songs)} songs, {missing} new since the last build (no decade or genre yet)")
    lock(songs, code)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lock"); p.add_argument("--code", required=True); p.add_argument("--songs", required=True)
    p.set_defaults(run=cmd_lock)
    p = sub.add_parser("unlock"); p.add_argument("--code", required=True); p.add_argument("--out", required=True)
    p.set_defaults(run=cmd_unlock)
    p = sub.add_parser("rekey"); p.add_argument("--old-code", required=True); p.add_argument("--code", required=True)
    p.set_defaults(run=cmd_rekey)
    p = sub.add_parser("update"); p.add_argument("--code", required=True)
    p.add_argument("--track"); p.add_argument("--artist")
    p.set_defaults(run=cmd_update)
    args = ap.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
