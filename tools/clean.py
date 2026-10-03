"""Turn the KJ's raw song-list exports into one clean, de-duplicated list.

The exports are tab-separated: title, artist, disc (or artist, title, disc).
Singers only need the title and the artist, so the disc column goes, and so do
the tags that only matter to whoever is running the track: backing vocals,
key changes, cut-downs, clean/explicit, solo/duet parts.
"""
import collections
import json
import re
import sys
import unicodedata

from rapidfuzz import fuzz, process


def decode(line):
    # The exports mix UTF-8 and Windows-1252 line by line.
    try:
        return line.decode("utf-8")
    except UnicodeDecodeError:
        return line.decode("cp1252", errors="replace")


def read_rows(path):
    raw = open(path, "rb").read().replace(b"\r\n", b"\n").split(b"\n")
    rows = []
    for line in raw:
        text = decode(line)
        if not text.strip() or text.startswith("#"):
            continue
        parts = text.split("\t")
        if len(parts) < 2:
            continue
        rows.append(parts)
    return rows


def load(track_path, artist_path):
    """Both exports hold the same songs; read whichever we were given."""
    rows = []
    if track_path:
        rows += [(p[0], p[1]) for p in read_rows(track_path)]
    if artist_path:
        rows += [(p[1], p[0]) for p in read_rows(artist_path)]
    return rows


# ---------------------------------------------------------------- tidying

QUOTES = str.maketrans({"‘": "'", "’": "'", "´": "'", "`": "'",
                        "“": '"', "”": '"', "–": "-", "—": "-",
                        " ": " "})


def tidy(s):
    s = s.translate(QUOTES).replace("�", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# A bracketed tag is dropped when it describes the backing track rather than
# the song. Anything else in brackets ("(Live)", "(Medley)", "(Part 2)",
# "(Taylor's Version)") is part of what the singer is choosing, so it stays.
PRODUCTION = re.compile(r"""
    backing | \bbvs?\b | vocals? | non\ vocal | \blyrics\b(?!.*(english|spanish))
  | semitone | \bkeys?\b\s*(of\b|:|down|up) | (fe)?male\ key | original\ key | lower\ key | ^key
  | harmon(y|ies)
  | \bcut\b | \bcuts\b
  | \bclean(er)?\b | explicit | swearing
  | \bduet\b | \bsolos?\b | \bduo\b | \btrio\b
  | \b(fe)?male\b | rapp(er|ing) | \brap\b
  | parts?\ only | separate\b.*\bparts | spoken\ parts? | voiceover | lead\ and | three\ male
  | justin\ &\ ludacris
  | album\ version | single\ (version|edit|mix) | radio\ edit$ | ^radio\ (edit|version)
  | original\ (version|slow\ version) | re-?recorded | remake | karaoke
  | ^(full|short|long|extended)(\ length)?(\ version)?$ | full\ length
  | ^(slow|fast|up\ ?tempo)(\ version)?$
  | ^\d{4}\ version$ | post\ \d{4}\ version | ^\d+\ version$
  | minus\ | ^with\ (no|full|piano|vocal|lead|fewer|'what') | with\ racist
  | no\ (echoes|chorus|sax|spoken|verse|swearing|big\ fat)
  | ^instrumental | ^vocal | ^backing$ | ^with\ no\ big\ fat\ woman$
  | sbi\ (mix|dance) | \bending\b | \bintro\b
  | ^[-+]\d+$ | ^without\b | ^with\ (echoes|silence|munchkins|gap|play\ off|music\ to\ end)
  | ^\d+\ verses$ | ^dvd$ | ^b5$ | ^orig\b | ^original$ | alternative\ take
""", re.I | re.X)


def strip_tags(title):
    def drop(m):
        inner = m.group(1)
        return " " if PRODUCTION.search(inner) else m.group(0)
    t = re.sub(r"\s*[\(\[]([^\)\]]*)[\)\]]", lambda m: " " + drop(m).strip() + " ", title)
    # An unclosed tag at the end: "You Are Not Alone (Duet Version"
    t = re.sub(r"\s*[\(\[]([^\)\]]*)$", lambda m: "" if PRODUCTION.search(m.group(1)) else m.group(0), t)
    # Tags tacked on with a dash: "Take A Message To Mary - With Harmony"
    t = re.sub(r"\s+-\s+(with|without|no)\s+(harmony|backing vocals?)$", "", t, flags=re.I)
    t = re.sub(r"\s+-\s+(?=\()", " ", t)
    return tidy(t)


def the_to_front(s):
    """'Beatles, The' -> 'The Beatles'; 'Things We Do For Love, The' too."""
    m = re.match(r"^(.*?),\s*(The|A|An)\s*((?:\s*[\(\[].*)?)$", s, re.I)
    if m and m.group(1):
        if re.match(r"(the|these|this|those|a|an)\b", m.group(1), re.I):
            return tidy(f"{m.group(1)} {m.group(3)}")  # "These Boots..., The": stray article
        art = m.group(2).capitalize()
        return tidy(f"{art} {m.group(1)} {m.group(3)}")
    # 'Beatles, The feat. Someone', 'Fureys, The & Davey Arthur'
    m = re.match(r"^(.*?),\s*The\s*((?:feat\b|ft\b|featuring\b|with\b|&|and\b|vs\b).*)$", s, re.I)
    if m:
        return tidy(f"The {m.group(1)} {m.group(2)}")
    return s


SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or",
         "the", "to", "vs", "with", "from", "into", "n'"}


def fix_shouting(s):
    """All-caps or all-lower names get title-cased; anything mixed is trusted."""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return s
    words = s.split(" ")
    if all(c.isupper() for c in letters) and len(letters) > 4:
        pass
    elif all(c.islower() for c in letters):
        pass
    elif len(words) >= 3 and all(not w[:1].isupper() for w in words[1:]):
        pass  # sentence case: "Tryin' to get to you"
    else:
        return s
    words = s.lower().split(" ")
    out = []
    for i, w in enumerate(words):
        if i and w in SMALL:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


# ---------------------------------------------------------------- matching keys

FEAT = re.compile(r"\s+(?:feat\.?|ft\.?|featuring|with|vs\.?|versus|duet with)\s+", re.I)


def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def key(s):
    s = fold(s)
    s = s.replace("&", " and ").replace("+", " and ")
    s = re.sub(r"'", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"^the ", "", s.strip())
    s = re.sub(r" the$", "", s)
    s = re.sub(r"\b(co|corp)$", "company", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def primary(artist):
    return FEAT.split(artist)[0]


def title_key(t):
    k = key(t)
    k = re.sub(r"\b(n|in)\b", "and", k)  # rock n roll / rock and roll
    return k.replace(" ", "")  # "Dance Floor" / "Dancefloor", "T.V." / "TV"


# ---------------------------------------------------------------- the pass


def repair_split_hyphens(rows):
    """'Spiller feat Sophie Ellis' / 'Bextor - Groovejet' -> one name again."""
    hyphen_words = set()
    for t, a in rows:
        for w in re.findall(r"[\w']+-[\w']+", a):
            hyphen_words.add(w.lower())
    out = []
    for t, a in rows:
        m = re.match(r"^([\w']+) - (.+)$", t)
        if m:
            last = a.split()[-1] if a.split() else ""
            joined = f"{last}-{m.group(1)}".lower()
            if joined in hyphen_words:
                a = f"{a}-{m.group(1)}"
                t = m.group(2)
        out.append((t, a))
    return out


JUNK_ARTISTS = {"ek"}

# Close spellings that are really different acts.
NEVER_FOLD = {frozenset(p) for p in [
    ("ryan adams", "bryan adams"), ("wilkinsons", "wilkinson"), ("promise", "promises"),
    ("johnny nash", "johnny cash"), ("willow smith", "will smith"),
]}


# Spellings the list gets wrong, and catalogue labels that are not acts.
ARTIST_NAMES = {
    "Liza Minelli": "Liza Minnelli", "Frankie Vaughn": "Frankie Vaughan",
    "Sugar Minnott": "Sugar Minott", "Paul Heaton And Jacqui Abbot": "Paul Heaton & Jacqui Abbott",
    "Derek & The Dominoes": "Derek & The Dominos", "Stereo McS": "Stereo MC's",
    "Medley & Warnes": "Bill Medley & Jennifer Warnes", "Kids Karaoke": "Children's Songs",
    "Sbi New Mix Based On Celine Dion Version": "Celine Dion", "T.V. Theme": "TV Themes",
    "Sophie Ellis Bextor": "Sophie Ellis-Bextor", "A-Ha": "a-ha",
}


# Copies where every spelling in the list is wrong, or the wrong one wins.
TITLES = {
    "Tryin' to Get to You": "Trying To Get To You", "That's What I Go To School For": "What I Go To School For",
    "Batchelor Boy": "Bachelor Boy", "That's What's I Go To School For": "What I Go To School For",
    "Point Of Authority": "Points Of Authority",
    "I'll Have To Say I'll Love You In A Song": "I'll Have To Say I Love You In A Song",
    "Who's Bed Have Your Boots Been Under": "Whose Bed Have Your Boots Been Under",
    "Queen Of My Double Wide Trailor": "Queen Of My Double Wide Trailer",
}


def rename(lead, credit=None):
    """Apply ARTIST_NAMES to a lead artist and, if given, the full credit."""
    new = ARTIST_NAMES.get(lead, lead)
    if credit is None:
        return new
    return new + credit[len(lead):] if credit.startswith(lead) else credit


def pick(variants):
    """Most common spelling wins; ties go to the one with more capitals."""
    c = collections.Counter(variants)
    return max(c, key=lambda v: (c[v], sum(ch.isupper() for ch in v[:1] + "".join(w[:1] for w in v.split())), len(v), v))


VERSION_WORDS = re.compile(r"\b(live|remix|mix|acoustic|medley|unplugged|demo|part|pt|version)\b", re.I)
LOWER_WORD = re.compile(r"(?<=\s)(?!(?:a|an|and|as|at|by|for|in|of|on|or|the|to|n')\b)[a-z]")


def best_title(titles, words):
    """Pick the spelling to show from the copies of one song.

    A misspelt word is rare across the whole list, so the copy whose rarest word
    is most common is the one spelt right; then proper casing, then the most copies.
    """
    c = collections.Counter(titles)

    def score(t):
        rarest = min((words[w] for w in key(t).split()), default=0)
        capitals = sum(ch.isupper() for ch in "".join(w[:1] for w in t.split()))
        return (rarest, not LOWER_WORD.search(t), c[t], capitals, len(t), t)
    return max(c, key=score)


def merge_typos(groups, words, log):
    """Same act, nearly the same title: one is a typo or a dropped word.

    "Can't Help Faling In Love" / "Falling", "Horse With No Name" / "A Horse...",
    "Livin' On A Prayer" / "Living". Live, remix and medley versions stay apart.
    """
    def tags(t):
        # Two songs run together ("Sally-In The Midnight Hour") are a medley.
        return {w.lower() for w in VERSION_WORDS.findall(t)}, "/" in t or " - " in t or re.search(r"[a-z]-[A-Z]", t) is not None

    def score(k):
        members = groups[k]
        t = best_title([t for t, _ in members], words)
        return (min((words[w] for w in key(t).split()), default=0), len(members), len(t), k)

    by_act = collections.defaultdict(list)
    for k in groups:
        by_act[k[1]].append(k)
    for ak, ks in by_act.items():
        if len(ks) < 2:
            continue
        ks.sort(key=score, reverse=True)
        for i, keep in enumerate(ks):
            if keep not in groups:
                continue
            for other in ks[i + 1:]:
                if other not in groups:
                    continue
                a, b = keep[0], other[0]
                if min(len(a), len(b)) < 8 or re.sub(r"\D", "", a) != re.sub(r"\D", "", b):
                    continue
                if fuzz.ratio(a, b) < 90:
                    continue
                ta, tb = (best_title([t for t, _ in groups[k]], words) for k in (keep, other))
                if tags(ta) != tags(tb):
                    continue
                print(f"  title   {tb!r} -> {ta!r}", file=log)
                groups[keep] += groups.pop(other)


def clean(rows, log=sys.stderr):
    rows = [(tidy(t), tidy(a)) for t, a in rows]
    rows = repair_split_hyphens(rows)
    rows = [(the_to_front(strip_tags(t)), the_to_front(a)) for t, a in rows]
    rows = [(fix_shouting(t), fix_shouting(a)) for t, a in rows if t and a and key(a) not in JUNK_ARTISTS]
    rows = [(TITLES.get(t, t), a) for t, a in rows]

    # --- artists: one spelling per act ---------------------------------
    by_key = collections.defaultdict(list)
    for t, a in rows:
        by_key[key(primary(a))].append(primary(a))
    keys = sorted(by_key, key=lambda k: (-len(by_key[k]), k))
    # Fold typos into the bigger spelling: "Martine McCuctheon" -> "McCutcheon".
    alias = {}
    big = [k for k in keys if len(k) >= 7]
    for k in keys:
        if k in alias or len(k) < 7:
            continue
        for other, score, _ in process.extract(k, big, scorer=fuzz.ratio, limit=5, score_cutoff=92):
            if other == k or other in alias:
                continue
            if len(by_key[other]) >= len(by_key[k]):
                continue
            # Never fold names that differ only by a number ("Boyz II Men", "112").
            if re.sub(r"\D", "", other) != re.sub(r"\D", "", k):
                continue
            if frozenset((other, k)) in NEVER_FOLD:
                continue
            alias[other] = k
            print(f"  artist  {pick(by_key[other])!r} -> {pick(by_key[k])!r}", file=log)

    def akey(a):
        k = key(primary(a))
        return alias.get(k, k)

    artist_names = collections.defaultdict(list)
    for t, a in rows:
        artist_names[akey(a)].append(primary(a))
    artist_display = {k: pick(v) for k, v in artist_names.items()}

    # --- songs: one row per title per act ------------------------------
    groups = collections.defaultdict(list)
    for t, a in rows:
        groups[(title_key(t), akey(a))].append((t, a))
    words = collections.Counter(w for t, _ in rows for w in key(t).split())
    merge_typos(groups, words, log)

    songs = []
    for (tk, ak), members in groups.items():
        title = best_title([t for t, _ in members], words)
        credits = [a for _, a in members]
        # Keep the featured credit if any copy has one: "Jay-Z feat. Beyonce".
        with_feat = [c for c in credits if FEAT.search(c)]
        lead = artist_display[ak]
        credit = lead
        if with_feat:
            best = pick(with_feat)
            m = FEAT.search(best)
            joiner = m.group(0).strip()
            if joiner.lower().startswith(("ft", "featuring", "feat")):
                joiner = "feat."
            credit = f"{lead} {joiner} {best[m.end():]}"
        songs.append({"t": title, "a": rename(lead, tidy(credit)), "p": rename(lead), "ak": ak, "tk": tk})

    # A rename can land two acts on one name ("Medley & Warnes"): one row each song.
    seen, unique = set(), []
    for s in sorted(songs, key=lambda s: (s["a"] == s["p"], s["tk"])):
        k = (title_key(s["t"]), key(s["p"]))
        if k not in seen:
            seen.add(k)
            unique.append(s)
    unique.sort(key=lambda s: (s["tk"], s["ak"]))
    return unique


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--track")
    ap.add_argument("--artist")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = load(args.track, args.artist)
    print(f"read {len(rows)} rows", file=sys.stderr)
    songs = clean(rows)
    print(f"kept {len(songs)} songs by {len({s['ak'] for s in songs})} artists", file=sys.stderr)
    json.dump(songs, open(args.out, "w"), ensure_ascii=False, indent=0)
