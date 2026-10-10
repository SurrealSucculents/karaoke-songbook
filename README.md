# Mad Dog Karaoke songbook

The song list on a phone. Guests scan the QR code on the table sheet,
and can then search every song by title or artist, browse A–Z by song or by artist, and narrow it down by genre and
decade.

Site: <https://maddogkaraoke.co.uk/>

## How the list is stored

`songbook.json` is the whole list, in the compact form the page reads. It is
plain and public: the page loads it directly and there is no code to type.
`tools/build.py` reads and writes the same file, so a rebuild never needs
anything but that file and the new export.

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
python3 tools/sheet.py --mono --out songbook-sheet-bw.pdf   # black-and-white printer
```

Page 1 is an A4 poster listing what the site does in big type (search, browse,
favourites, picks, listen, karaoke nights). Page 2 is four A6 table cards to cut
out. The song count on it comes from `songbook.json`, so reprint after a big
update.
`.gitignore` keeps PDFs out of the repo.

To add a second QR code that joins the venue's Wi-Fi (handy where phone signal
is poor), pass the network and password. They go on the printout only and are
never saved in the repo:

```sh
python3 tools/sheet.py --wifi-name "Venue Guest" --wifi-password secret
```

## Load a new export from the KJ software

Put the export (e.g. `Songlist-fulltrack.txt`) in the `import/` folder and push
it to `main` (on GitHub: **Add file → Upload files**, into `import/`). The
**Rebuild the songbook** workflow rebuilds `songbook.json`, commits it and removes
the export. The list is public, so the export being in the commit history is
fine. To do it by hand instead:

```sh
python3 tools/build.py update --track Songlist-fulltrack.txt
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
tagged they don't appear under a genre or decade filter. To tag them, export the list, fill in `y` (year), `g` (genre, one of the names in
`tools/build.py`) and `v` (singer: 1 male, 2 female, 3 duet), and pack it again:

```sh
python3 tools/build.py export --out songs.json
# edit songs.json
python3 tools/build.py pack --songs songs.json
```

`songs.json` is only a working copy, so it's in `.gitignore`.

## Singer filter

Each song has a singer type: male, female or duet. It comes from, in order: a
"(Duet)", "(Male)" or "(Female)" tag in the title of the KJ export, what the
list already had, and `tools/artist_voices.json`, a lookup of acts that are
male (`m`), female (`f`) or a male and female duo (`d`). Acts that aren't listed
there (mixed bands, medleys, anything unsure) have no singer type. The lookup
was filled in from general knowledge, so correct it where it's wrong, then run
`python3 tools/build.py voices` to apply it to songs that have no type yet. To
re-apply it to every song after correcting an act, use `voices --reset` (this also
clears types that came from export titles, so load the export again after).
`d` is only for a male and female pair who sing together; a DJ or producer with
a guest vocalist takes the singer's type instead.

## Karaoke nights

The upcoming dates run along the bottom of the page, just for show. A shared
dates link (`?dates`) opens them as a full list.
They live in `schedule.json`, one `YYYY-MM-DD` per night:

```json
{"venue": "The Lugger Inn", "nights": ["2026-10-23", "2026-10-24"]}
```

`venue` shows under each date and in shared date lists; leave it out to show
dates only.

Edit it on GitHub (pencil icon) and commit to `main`. Past dates drop off by
themselves at midnight, so old ones can stay in the file. If the file is missing
or empty, the strip just doesn't show.

## Sharing

The **Share** button at the top, the **Share** link on a song and **Share the
dates** (on a shared dates link) use the phone's own share menu (WhatsApp, Messages…), or copy the link
where there isn't one. Shared links open straight onto the song
(`?song=…&by=…`) or the list of dates (`?dates`).

## Favourites and For you

Tap the ♡ on any song (or **Save** on the song itself). Saved songs are pinned in
a **Your saved songs** section at the top of the Songs list, and stay in their
A–Z place too. They're kept in the browser on that phone (`localStorage`), so
there are no accounts and nothing is sent anywhere. They stay until the guest
clears their browser data. Safari on iPhone can clear a site's stored data after
about 7 days of use without a visit, so **Share my saved songs** (on the Songs tab)
sends a link with the songs in it: opening it on any phone offers to save them
again. Saved songs are matched by title and artist, so rebuilding the song list
doesn't lose them.

The **For you** tab is the full list of songs recommended from what's saved,
best first. There are no play counts, so it matches on what each song is: the
same acts, genres, decades and singer types as the saved songs, with a nudge for
acts that have a big catalogue. The top of the list alternates more from acts
they've saved with acts new to them (at most two songs from any saved act, one
from a new act); after that it's everything else that matched, best first. It
changes a little each day, and **Refresh** reshuffles. It all runs on the phone;
nothing is sent anywhere.

**Fine tune my recommendations** (the sliders button next to Share) asks the
decade the guest was born, whether they like songs sung by men, women or duets,
and their voice type (soprano, mezzo, alto, tenor, baritone, bass). Each is
optional. For you then favours songs from their teens and twenties, leaves out
songs by the other sex (duets stay in), and favours acts with the same voice
type or the one next to it. It works with no saved songs at all; with saved
songs, it steers those picks. The answers are kept on the phone, like saved
songs, and a pink dot on the button shows they're set.

Voice types come from `tools/artist_ranges.json`, the lead singer's usual voice
type for the acts with the most songs (about half the list). Like the singer
lookup it was filled in from general knowledge, so correct it where it's wrong
and run `python3 tools/build.py ranges` (any rebuild also picks it up). Acts not
listed simply aren't scored on voice type.

## Listen to a song

**Listen to song** on a song card lists Spotify, Apple Music and YouTube, with
**Show more apps** for YouTube Music, Amazon Music, Deezer and SoundCloud. Each link searches that app for the title and artist ("feat."
credits and bracketed notes left out); on a phone with the app installed it
opens in the app. Add, remove or reorder apps in `LISTEN` in `index.html`; `LISTEN_FIRST` is how many show
before "Show more apps".

## Files

| | |
|---|---|
| `index.html` | the whole site: list, search, filters, dates, sharing |
| `songbook.json` | the song list |
| `schedule.json` | the karaoke nights |
| `tools/clean.py` | turns a raw export into a clean, de-duplicated list |
| `tools/build.py` | update / export / pack `songbook.json` |
| `tools/artist_voices.json` | singer type per act, for the Singer filter |
| `tools/artist_ranges.json` | voice type per act, for Fine tune |
| `tools/sheet.py` | the printable QR sheet |
