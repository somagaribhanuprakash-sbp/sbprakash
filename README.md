# OPS // TRACK — v3.0 (Full-stack Edition)

Your schedule, session tracker, security project log, and 20-week restart plan —
rebuilt with a real Python backend so your data survives browser clears, phone
resets, and cache wipes. Same look, same tabs, all the old features kept, plus
fixes and new ones.

## What changed from v2.0

**Bugs fixed**
- **Stored XSS**: v2.0 wrote event titles, project names, descriptions, etc.
  straight into `innerHTML`. A title like `<img src=x onerror=alert(1)>` would
  execute. Every user-supplied string is now HTML-escaped before rendering.
- **Events could only be added to "today"** and `deleteEvent` only ever looked
  at today's list — creating or removing an event for any other date silently
  failed. Events now carry a real `date` field end-to-end.
- **All data lived in `localStorage`** — clearing site data, reinstalling the
  PWA, or switching devices wiped everything with no way back short of a
  manual backup file. Data now lives server-side in SQLite.
- **The Restart Plan existed in two disconnected places** (`index.html`'s
  simple 5-item-per-phase list, and `plan.html`'s real week-by-day list),
  with two different `localStorage` keys that never synced. There's now one
  plan (the detailed one), served from the backend, checked off in one place.
- No input validation anywhere (empty titles, end-before-start times, garbage
  numbers) — now validated both client- and server-side.

**New**
- Flask REST API + SQLite backend (`/backend`)
- Edit/delete on security projects, learning items, and portfolio projects
  (v2.0 could only add, never remove, most of these)
- Status cycling on security projects (In Progress → Completed → Paused)
- Streak, today's hours, and event counts computed server-side from real data
  instead of only ever looking at "today"
- A real offline-capable service worker (the old one was a pass-through stub)
- Optional bearer-token auth for the API (`OPSTRACK_TOKEN`)
- Backup/restore now round-trips through the server instead of just the browser
- Refreshed app icon (same terminal-glyph identity, cleaner geometry, proper
  maskable variant for Android)

## Architecture

```
opstrack/
├── backend/            Flask API + SQLite (the only thing that needs Python hosting)
│   ├── app.py
│   ├── models.py
│   ├── restart_plan.py
│   └── requirements.txt
├── frontend/            Static HTML/CSS/JS — deployable anywhere static files are served
│   ├── index.html
│   ├── app.js
│   ├── manifest.json
│   ├── sw.js
│   └── icons/
├── Procfile              For Render/Railway/Heroku-style buildpacks
└── render.yaml           One-file Render.com deploy config
```

The frontend talks to the backend purely over `fetch()` — it never touches
the filesystem or a database directly. This means you can host the two
pieces separately or together.

## Running it locally

```bash
cd backend
pip install -r requirements.txt
python app.py            # http://localhost:5000 — serves both the API and the frontend
```

Open `http://localhost:5000` — that's it, one process, no separate frontend
server needed for local use.

## Deploying

**Important:** Netlify does not run Python. If you deploy the frontend to
Netlify, the backend needs to live somewhere that runs a real server process
— Render, Railway, Fly.io, or a VPS all work well and have free/cheap tiers.
The two options below cover both cases.

### Option A — everything on one host (simplest)

Deploy the whole `opstrack/` folder to **Render** (or Railway/Fly):

1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service**, connect the repo. It'll pick up
   `render.yaml` automatically (Build: `pip install -r backend/requirements.txt`,
   Start: `gunicorn app:app --chdir backend --bind 0.0.0.0:$PORT`).
3. Render's free disks are ephemeral on redeploy — for real persistence, add
   a small persistent disk (the `render.yaml` here already requests one) and
   set `OPSTRACK_DB=/opt/render/project/src/backend/data/opstrack.db` as an
   env var so the SQLite file lives on it.
4. Optionally set `OPSTRACK_TOKEN` to a long random string to require auth —
   if you do, enter the same value in the app's **Settings → Access Token**.
5. Visit the Render URL — frontend and API are served from the same origin,
   so nothing else to configure.

### Option B — frontend on Netlify, backend on Render

1. Deploy `backend/` to Render exactly as above (steps 1–4), note the URL
   (e.g. `https://opstrack-api.onrender.com`).
2. Drag the `frontend/` folder onto **https://app.netlify.com/drop**, or
   connect the repo with **Base directory: frontend**, no build command.
3. Open the deployed Netlify site → **Settings tab → API Base URL** → paste
   the Render URL → **Save & Reconnect**. This is stored in the browser and
   points the static frontend at your backend from then on.
4. If you set `OPSTRACK_TOKEN` on the backend, also set
   `OPSTRACK_CORS_ORIGIN` on Render to your exact Netlify URL (instead of
   `*`) and paste the token into the frontend's Settings tab.

### Self-hosting

```bash
pip install -r backend/requirements.txt
gunicorn app:app --chdir backend --bind 0.0.0.0:8000
```
Put nginx/Caddy in front of it for TLS, or serve `frontend/` separately and
point it at wherever the API ends up.

## Environment variables (backend)

| Variable | Purpose | Default |
|---|---|---|
| `OPSTRACK_DB` | Path to the SQLite file | `backend/opstrack.db` |
| `OPSTRACK_TOKEN` | If set, all `/api/*` routes require `Authorization: Bearer <token>` | unset (open) |
| `OPSTRACK_CORS_ORIGIN` | Allowed origin for CORS | `*` |
| `PORT` | Port to bind (set automatically by most hosts) | `5000` |

For a single-user personal tool, leaving `OPSTRACK_TOKEN` unset is fine as
long as the URL isn't shared. If you're putting this somewhere public,
set it.

## Data & backups

- Everything lives in SQLite on the backend. `Settings → Download Backup`
  pulls a full JSON snapshot from the server; `Restore Backup` uploads one
  and replaces everything currently stored.
- There's no scheduled backup job — download one occasionally, same as before.

## Notes on `plan.html`

The original `plan.html` (a standalone, more detailed restart-plan page) has
been merged into the main app's **Restart** tab, backed by the same API —
see "Bugs fixed" above for why. You don't need `plan.html` anymore; the
`/api/restart/plan` and `/api/restart/progress` endpoints are the single
source of truth now.
