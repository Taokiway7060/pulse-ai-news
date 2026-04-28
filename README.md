# Pulse — AI News, Daily

A free, static, glassmorphism-themed AI news site that auto-refreshes once a day from RSS feeds. Hosted on GitHub Pages.

```
+-------------------+      +------------------+      +-------------------+
|  RSS feeds        |  →   |  GitHub Actions  |  →   |  GitHub Pages     |
|  (TC, Verge, etc) |      |  (daily 06:00 UTC|      |  (free static     |
|                   |      |   build.py run)  |      |   hosting)        |
+-------------------+      +------------------+      +-------------------+
```

No backend. No database. One free account (GitHub).

## What's in this folder

- `index.html` / `styles.css` / `app.js` — the static frontend
- `build.py` — Python script that fetches feeds and writes `data/news.json` + `data/news.js`
- `requirements.txt` — Python deps (just `feedparser`)
- `data/news.json` + `data/news.js` — generated daily; seeded with placeholder content
- `.github/workflows/update.yml` — daily cron that runs `build.py` and commits

## Run it locally

Just double-click `index.html` — it loads `data/news.js` directly from disk so it works without a server.

To regenerate the data against live feeds:

```bash
pip install -r requirements.txt
python build.py
```

## One-time deploy with GitHub Pages (free)

### 1. Create the repo and upload the files

- Go to **github.com → New repository → Public**, name it `pulse-ai-news` (or anything).
- Click **uploading an existing file**, drag the entire project folder contents in, commit.

### 2. Enable Pages

- Repo **Settings → Pages**.
- Source: **Deploy from a branch**.
- Branch: `main`, folder: `/ (root)`. Save.
- Within ~30 seconds you'll get a URL like `https://<your-username>.github.io/pulse-ai-news/`.

### 3. The daily cron is already wired

The workflow at `.github/workflows/update.yml` runs at 06:00 UTC daily. It fetches RSS, regenerates `data/news.json` + `data/news.js`, and commits — which triggers Pages to redeploy automatically.

You can also trigger it on demand from **GitHub → Actions → Update AI News → Run workflow**.

## Customizing

- **Add or remove feeds:** edit the `FEEDS` list at the top of `build.py`. Each entry has a `name`, `url`, and `category`.
- **Tweak the look:** colors, blur, and gradient stops live in `styles.css` under `:root` (dark) and `[data-theme="light"]` (light).
- **Change the schedule:** the cron in `.github/workflows/update.yml`.

## Tech notes

- Single-page static site, no framework. Renders client-side from `data/news.js` (preferred, works on `file://`) or `data/news.json` (fetch fallback).
- `localStorage`/`sessionStorage` are intentionally not used; theme resets on reload.
- Per-feed entry cap (12) prevents arXiv from drowning slower feeds; total cap (120) keeps the page snappy.
