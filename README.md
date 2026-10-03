# Karaoke songbook

The venue's song list on a phone. Guests scan the QR code on the table sheet,
type the 6-digit code printed under it, and can then search every song by title
or artist, browse A–Z by song or by artist, and narrow it down by genre and
decade.

Site: <https://surrealsucculents.github.io/karaoke-songbook/>

## How the code protects the list

The list is never in this repo or on the site in readable form. `songbook.bin`
is the list gzipped and encrypted with AES-256-GCM, under a key derived from
the 6-digit code with PBKDF2-SHA256 (310,000 rounds). The page decrypts it in
the browser once the right code is typed, and remembers the code on that phone
until the code is changed or someone taps "Forget the code on this phone".

A 6-digit code keeps out anyone who only has the link. It won't stop someone
determined to brute-force the file, and anyone with the code can read the list.
Change the code whenever you like (below) and reprint the sheet.

## Setup

```sh
pip install -r requirements.txt
```

Turn on GitHub Pages once: **Settings → Pages → Build and deployment →
Deploy from a branch → `main` / `(root)`**. Every push to `main` then goes live
within a minute or two.

## Print the sheet

```sh
python3 tools/sheet.py --code 123456 --out songbook-sheet.pdf
```

Page 1 is an A4 poster. Page 2 is four A6 table cards to cut out. The PDF has
the code on it, so `.gitignore` keeps PDFs out of the repo.

## Change the code

```sh
python3 tools/build.py rekey --old-code 123456 --code 654321
git commit -am "Change the songbook code" && git push
python3 tools/sheet.py --code 654321
```

Phones that remembered the old code are asked for the new one.

## Load a new export from the KJ software

```sh
python3 tools/build.py update --code 123456 --track Songlist-fulltrack.txt
git commit -am "Update the song list" && git push
```

`update` runs the export through `tools/clean.py` and keeps the decade and
genre of every song it already knows. The cleaning step:

- drops the disc/manufacturer column (Zoom, Sunfly, SBI, Mr Entertainer…)
- strips tags that describe the backing track rather than the song: with/without
  backing vocals, harmonies, key changes, cut-downs, clean/explicit, solo/duet
  parts, album/single/radio versions
- keeps tags that change what you'd sing: Live, Acoustic, Remix, Medley, Part 2…
- folds duplicates and misspellings together ("Micheal Jackson", "Beatles, The",
  "Murder On The Dancefloor" / "Dance Floor")

New songs show up in search and the A–Z lists straight away. Until they're
tagged they don't appear under a genre or decade filter. To tag them, unlock the
list, fill in `y` (year) and `g` (genre, one of the names in `tools/build.py`),
and lock it again:

```sh
python3 tools/build.py unlock --code 123456 --out songs.json
# edit songs.json
python3 tools/build.py lock --code 123456 --songs songs.json
```

`songs.json` is unencrypted, so it's in `.gitignore`. Don't commit it.

## Files

| | |
|---|---|
| `index.html` | the whole site: code screen, list, search, filters |
| `songbook.bin` | the encrypted song list |
| `tools/clean.py` | turns a raw export into a clean, de-duplicated list |
| `tools/build.py` | lock / unlock / rekey / update `songbook.bin` |
| `tools/sheet.py` | the printable QR sheet |
