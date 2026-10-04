"""Keep the song list up to date.

songbook.json is the list, in the compact form the page reads. It's public and
plain: the page loads it directly, and every command here reads and writes it.

    # The KJ software exported a new list: re-clean it, keep every decade and
    # genre already known, rewrite songbook.json
    python3 tools/build.py update --track Songlist-fulltrack.txt

    # Get the list out as plain songs, to check or hand-edit it
    python3 tools/build.py export --out songs.json

    # Write an edited songs.json back as songbook.json
    python3 tools/build.py pack --songs songs.json
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import clean  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, "songbook.json")

GENRES = ["Pop", "Rock", "Indie & Alternative", "Dance", "R&B & Soul", "Hip-Hop & Rap",
          "Country", "Musicals & Film", "Christmas", "Swing & Easy Listening",
          "Folk & Irish", "Reggae & Ska", "Latin", "Novelty & Kids"]


def sort_key(s):
    k = clean.fold(s)
    k = re.sub(r"[^a-z0-9 ]+", "", k).strip()
    return k


def artist_sort_key(s):
    return re.sub(r"^the ", "", sort_key(s))


# ---------------------------------------------------------------- payload

def pack(songs):
    """[{t, a, p, y, g, v}] -> compact JSON the page reads.

    v is the singer type: 0 unknown, 1 male, 2 female, 3 duet.
    """
    artists = sorted({s["p"] for s in songs}, key=lambda a: (artist_sort_key(a), a))
    index = {a: i for i, a in enumerate(artists)}
    rows = []
    for s in sorted(songs, key=lambda s: (sort_key(s["t"]), artist_sort_key(s["p"]))):
        g = GENRES.index(s["g"]) if s.get("g") in GENRES else -1
        row = [s["t"], index[s["p"]], int(s.get("y") or 0), g, int(s.get("v") or 0)]
        if s["a"] != s["p"]:
            row.append(s["a"])
        rows.append(row)
    return {"v": 2, "g": GENRES, "a": artists, "s": rows}


def unpack(payload):
    artists, genres = payload["a"], payload["g"]
    songs = []
    v2 = payload.get("v", 1) >= 2
    for row in payload["s"]:
        t, ai, y, g = row[:4]
        p = artists[ai]
        v, credit = (row[4], row[5] if len(row) > 5 else p) if v2 else (0, row[4] if len(row) > 4 else p)
        songs.append({"t": t, "p": p, "a": credit, "y": y or None,
                      "g": genres[g] if g >= 0 else None, "v": v})
    return songs


def save(songs):
    with open(LIST, "w", encoding="utf-8") as f:
        json.dump(pack(songs), f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(songs)} songs to {os.path.relpath(LIST)} ({os.path.getsize(LIST) // 1024} KB)")


def load_list():
    with open(LIST, encoding="utf-8") as f:
        return unpack(json.load(f))


# ---------------------------------------------------------------- commands

def cmd_pack(args):
    songs = json.load(open(args.songs))
    for s in songs:
        s.setdefault("a", s["p"])
    save(songs)


def cmd_export(args):
    songs = load_list()
    json.dump(songs, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {len(songs)} songs to {args.out}")


def cmd_update(args):
    known = {}
    for s in load_list():
        known[(clean.title_key(s["t"]), clean.key(s["p"]))] = s
    fresh = clean.clean(clean.load(args.track, args.artist))
    songs, missing = [], 0
    for s in fresh:
        old = known.get((clean.title_key(s["t"]), clean.key(s["p"]))) or known.get((s["tk"], clean.key(s["p"])))
        y, g = (old["y"], old["g"]) if old else (None, None)
        missing += old is None
        # A tag in the fresh title wins; otherwise keep what was known.
        v = s.get("v") or (old.get("v", 0) if old else 0)
        songs.append({"t": s["t"], "a": s["a"], "p": s["p"], "y": y, "g": g, "v": v})
    print(f"{len(songs)} songs, {missing} new since the last build (no decade or genre yet)")
    save(songs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack"); p.add_argument("--songs", required=True)
    p.set_defaults(run=cmd_pack)
    p = sub.add_parser("export"); p.add_argument("--out", required=True)
    p.set_defaults(run=cmd_export)
    p = sub.add_parser("update")
    p.add_argument("--track"); p.add_argument("--artist")
    p.set_defaults(run=cmd_update)
    args = ap.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
