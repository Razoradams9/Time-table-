# Deploying the Timetable System

Architecture for the prototype:

- **Frontend** (React/Vite) → **Vercel**
- **Backend** (FastAPI + OR-Tools) → **Fly.io** (kept always-on)
- **Database** (Postgres) → **Neon** (free tier)

Local dev still uses SQLite + the Vite proxy — nothing to change for that.

---

## 0. Push to GitHub (one time)

From the project root (`time table/`):

```bash
git init
git add .
git commit -m "Timetable system: FastAPI + React, deploy-ready"
git branch -M main
git remote add origin https://github.com/Razoradams9/Time-table-.git
git push -u origin main
```

---

## 1. Database — Neon (free Postgres)

1. Sign up at https://neon.tech → **New Project**.
2. Copy the **connection string** (looks like
   `postgresql://user:pass@ep-xxx.aws.neon.tech/dbname?sslmode=require`).
3. Keep it handy for step 2.

---

## 2. Backend — Fly.io

Install the CLI and log in:

```bash
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
fly auth signup   # or: fly auth login
```

From the `backend/` folder:

```bash
cd backend
fly launch --no-deploy        # pick a UNIQUE app name + a region near you
                              # (it reuses the existing Dockerfile and fly.toml)
```

Set secrets (use YOUR Neon URL and a long random secret):

```bash
fly secrets set DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require"
fly secrets set SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
fly secrets set CORS_ORIGINS="https://YOUR-VERCEL-APP.vercel.app"
```

Deploy, then seed once:

```bash
fly deploy
fly ssh console -C "python seed_once.py"   # loads the 14 teachers + data (only if empty)
```

Your backend is now at `https://<your-app-name>.fly.dev`. Check
`https://<your-app-name>.fly.dev/api/health`.

> After the first deploy, update `CORS_ORIGINS` to the real Vercel URL from
> step 3 and run `fly deploy` again (or `fly secrets set` triggers a redeploy).

---

## 3. Frontend — Vercel

1. Go to https://vercel.com → **Add New → Project** → import the GitHub repo.
2. **Root Directory:** set to `frontend`.
3. Framework preset: **Vite** (auto-detected). Build command `npm run build`,
   output `dist` (from `vercel.json`).
4. **Environment Variable:**
   - `VITE_API_URL` = `https://<your-app-name>.fly.dev`  (no trailing slash)
5. **Deploy.**

Vercel gives you `https://<project>.vercel.app`. Put that back into the
backend's `CORS_ORIGINS` (step 2) if you haven't yet.

---

## 4. Verify

1. Open the Vercel URL.
2. Log in: `anjana@college.edu` / `password123`.
3. **Timetable → Regenerate** to build the schedule.
4. Try a leave + check auto-substitution.

---

## Keeping it 24/7

- `fly.toml` sets `min_machines_running = 1`, so the backend stays warm.
- Vercel frontends are always-on by default.
- If you ever see the backend sleeping, confirm `min_machines_running = 1` and
  that you're on a plan that allows it.

## Custom domain (later)

- **Vercel:** Project → Settings → Domains → add your domain, follow DNS steps.
- **Fly:** `fly certs add api.yourdomain.com` and point DNS, then set
  `VITE_API_URL` to the custom API domain.

## Notes

- `seed.py` **wipes and recreates** the DB — local only.
- `seed_once.py` is **safe for production** — seeds only when empty.
- The frontend auto-signs in as `anjana@college.edu` / `password123` (there is
  no login screen). Anyone with the site URL gets admin access, so do not
  expose a public deployment without adding access control.
