# Mad Dog Karaoke songbook

The song list on a phone. Guests scan the QR code on the table sheet,
and can then search every song by title or artist, browse A–Z by song or by artist, and narrow it down by genre and
decade.

Site: <https://maddogkaraoke.co.uk/>

## How the list is stored

The list is never in this repo or on the site in readable form. `songbook.bin`
is the list gzipped and encrypted with AES-256-GCM, under a key derived from
a 6-digit code with PBKDF2-SHA256 (310,000 rounds). Guests are not asked for the
code: it is built into `index.html` (`CODE`), and the page decrypts the list in
the browser as it loads.

That keeps the list out of the repo as plain text, but anyone who views the
page source can find the code and read the list. If you change the code
(below), update `CODE` in `index.html` too.

## Setup

```sh
pip install -r requirements.txt
```

Turn on GitHub Pages once: **Settings → Pages → Build and deployment →
Deploy from a branch → `main` / `(root)`**. Every push to `main` then goes live
within a minute or two.

The site is served on `maddogkaraoke.co.uk` (the `CNAME` file). At the domain's
DNS (GoDaddy), the bare domain `@` has four A records — `185.199.108.153`,
`185.199.109.153`, `185.199.110.153`, `185.199.111.153` — and `www` is a CNAME
to `surrealsucculents.github.io`. With **Enforce HTTPS** ticked in the Pages
settings, GitHub issues and renews the certificate itself.

## Print the sheet

```sh
python3 tools/sheet.py --out songbook-sheet.pdf
```

Page 1 is an A4 poster. Page 2 is four A6 table cards to cut out.
`.gitignore` keeps PDFs out of the repo.

To add a second QR code that joins the venue's Wi-Fi (handy where phone signal
is poor), pass the network and password. They go on the printout only and are
never saved in the repo:

```sh
python3 tools/sheet.py --wifi-name "Venue Guest" --wifi-password secret
```

## Change the code

```sh
python3 tools/build.py rekey --old-code 123456 --code 654321
```

Then set `CODE` in `index.html` to the new code, and commit and push both files
together.

## Load a new export from the KJ software

Put the export (e.g. `Songlist-fulltrack.txt`) in the `import/` folder and push
it to `main` (on GitHub: **Add file → Upload files**, into `import/`). The
**Rebuild the songbook** workflow rebuilds `songbook.bin`, commits it and removes
the export. The list is public, so the export being in the commit history is
fine. To do it by hand instead:

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
