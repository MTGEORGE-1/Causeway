# Deploying Causeway

The site is static. There is no backend, no server and no database — a scheduled
job rebuilds one file each night and GitHub serves it.

```
GitHub Actions  ──►  runs run.py  ──►  uploads site/  ──►  GitHub Pages
 (22:00 UTC, Mon-Fri)                                       (public URL)
```

Cost: **$0**. Both Actions and Pages are free at this scale.

---

## One-time setup

### 1. Create the repo on GitHub

Go to <https://github.com/new>. Name it `causeway`.
**Do not** tick "Add a README" — this folder already has one.

### 2. Push

A local git repo already exists here with everything committed. Point it at
GitHub and push — substitute your username:

```bash
cd "/Users/micahgeorge/Desktop/PROJECT "
git remote add origin https://github.com/YOUR-USERNAME/causeway.git
git branch -M main
git push -u origin main
```

### 3. Turn on Pages

In the repo: **Settings → Pages → Build and deployment → Source**, choose
**GitHub Actions**. Not "Deploy from a branch" — the workflow uploads the built
site directly, so there is no branch to deploy from.

### 4. Run it once

**Actions** tab → **Build and deploy** → **Run workflow**. Takes two or three
minutes. When it finishes your site is at:

```
https://YOUR-USERNAME.github.io/causeway/
```

That URL is public. Anyone you send it to can open it — no account needed.

---

## After that

It rebuilds itself at 22:00 UTC every weekday (after the US close, so the ADR
prices have settled). You do nothing. Open the URL and it shows last night's
build.

To force a refresh, hit **Run workflow** again.

To change the schedule, edit the `cron` line in
[.github/workflows/build.yml](.github/workflows/build.yml). The format is
`minute hour day month weekday`, in UTC.

---

## The thing to check on the first run

The workflow probes every data source before building and saves the result.
GitHub's runners are **not** behind the WatchGuard firewall that geo-blocks
China-hosted IPs on your network, so the A-share sources that fail on your
laptop may work there.

To find out: open the completed run in the **Actions** tab and download the
**data-source-audit** artifact. Open the JSON and look at the entries that fail
locally:

- `akshare: A-share spot (EastMoney)`
- `akshare: BYD daily history (002594)`
- `akshare: SMIC daily history (688981)`

**If those say `OK`**, the deployed site can carry the full mainland dataset —
Cambricon, Hygon, NAURA, AMEC, and the A-H premium feature. Worth doing, because
Cambricon is the single cleanest illustration of the project's thesis. The
universe already stores `a_share` codes for every name that has one, so wiring
it up is an ingest change, not a rewrite.

**If they say `FAIL`**, the endpoints rate-limit cloud IPs too, and the HK/ADR
universe stays as it is. Not a problem — just worth knowing rather than guessing.

---

## Notes

- Build outputs (`site/data.js`, `data/`) are gitignored on purpose. They are
  regenerated every run, and committing them nightly would grow the repo by
  ~200KB a day for no benefit.
- After cloning fresh, run `python run.py` once before opening
  `site/index.html` locally — otherwise `data.js` does not exist yet and the
  page will tell you so.
- The published page makes no network calls of its own. It cannot break because
  a data source is down; it can only go stale.
