# Deployment Guide

- **Frontend** → Vercel (free)
- **Backend** → Render (free web service, Docker)
- **Database** → Neon (free Postgres)

---

## Step 1 — Push to GitHub

Make sure all changes are committed and pushed:

```bash
git add .
git commit -m "deploy: all features"
git push
```

---

## Step 2 — Database (Neon)

1. Sign up at https://neon.tech → **New project**.
2. Copy the **connection string** — it looks like:
   `postgresql://user:pass@ep-xxx.aws.neon.tech/dbname?sslmode=require`
3. Keep it for the next step.

---

## Step 3 — Backend (Render)

1. Go to https://render.com → **New → Web Service**.
2. Connect your GitHub repo.
3. Settings:
   - **Name:** `timetable-backend` (or anything you like)
   - **Region:** pick the closest to you
   - **Branch:** `main`
   - **Runtime:** Docker
   - **Dockerfile path:** `./backend/Dockerfile`
   - **Docker context:** `./backend`
   - **Instance type:** Free
4. Add these **Environment Variables** (in the Render dashboard):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | your Neon connection string |
   | `SECRET_KEY` | any long random string (32+ chars) |
   | `CORS_ORIGINS` | `*` for now (update after Vercel deploy) |

5. Click **Create Web Service**. Render builds the Docker image, runs
   `seed_once.py` automatically on first boot, then starts the server.
6. Your backend URL will be `https://timetable-backend.onrender.com`
   (or whatever name you chose). Test it:
   `https://<your-service>.onrender.com/api/health`

> **Free tier note:** Render's free tier spins down after 15 minutes of
> inactivity. First request after sleep takes ~30 seconds. Upgrade to the
> $7/month Starter plan to keep it always on.

---

## Step 4 — Frontend (Vercel)

1. Go to https://vercel.com → **Add New → Project** → import the GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework: **Vite** (auto-detected). Build command `npm run build`, output `dist`.
4. Add this **Environment Variable**:

   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://<your-render-service>.onrender.com` |

5. Click **Deploy**.
6. Your frontend URL will be `https://<project>.vercel.app`.

---

## Step 5 — Wire CORS

Once you have the Vercel URL, go back to Render → your service →
**Environment** → update `CORS_ORIGINS` to:

```
https://<your-project>.vercel.app
```

Render will redeploy automatically.

---

## Step 6 — Verify

1. Open the Vercel URL.
2. Log in: `anjana@college.edu` / `password123` (HOD).
3. Go to **Timetable** — the 218-period schedule should be there.
4. Try registering a leave and check that substitutions and make-ups are created.
5. Log out and log back in as a teacher (e.g. `nisha@college.edu` / `password123`)
   to check the restricted teacher portal.

---

## Credentials (change these after first login)

| Email | Password | Role |
|-------|----------|------|
| anjana@college.edu | password123 | HOD / Admin |
| rajeev@college.edu | password123 | Teacher |
| hari@college.edu | password123 | Teacher |
| spurgen@college.edu | password123 | Teacher |
| meenu@college.edu | password123 | Teacher |
| joseph@college.edu | password123 | Teacher |
| soumya@college.edu | password123 | Teacher |
| andal@college.edu | password123 | Teacher |
| sameeran@college.edu | password123 | Teacher |
| sruthi@college.edu | password123 | Teacher |
| nisha@college.edu | password123 | Teacher |
| sanjay@college.edu | password123 | Teacher |
| vipin@college.edu | password123 | Teacher |
| mani@college.edu | password123 | Teacher |

---

## Local development

Backend:
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010
```

Frontend:
```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. The Vite proxy forwards `/api` to port 8010.
