# College Timetable & Smart Substitution System

A web app where teachers follow a fixed weekly timetable. When a teacher
registers a leave, the system automatically finds suitable substitutes (using
fair, auditable rules) and updates that day's schedule. Three concerns: Teacher,
HOD/Admin, and the automated substitution engine.

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React + Vite | Fast dev, tiny build, mobile-responsive UI |
| Backend | FastAPI (Python) | First-class OR-Tools support, async, typed |
| Database | SQLite (dev) | Zero setup; schema is portable to PostgreSQL |
| Solver | Google OR-Tools CP-SAT | Conflict-free timetable generation |
| Substitution | Rule-based engine | Predictable, auditable (Req 6.3) |
| AI layer | Deterministic explainer/suggester | No API key, no cost, natural-language output |
| Notifications | In-app + email | Email logs to console if SMTP unset |

## Prerequisites

- Python 3.9+ (tested on 3.14) available as `py` or `python`
- Node.js 18+ and npm

## Run the backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed.py          # create + seed the database
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010
```

API docs: http://localhost:8010/docs

> The frontend dev server proxies `/api` to port **8010**. If you change the
> backend port, update `frontend/vite.config.js`.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Demo logins (password: `password123`)

| Role | Email |
| --- | --- |
| HOD/Admin | hod@college.edu |
| Teacher | asha@college.edu, bala@college.edu, chitra@college.edu, deepak@college.edu, esha@college.edu |

## Try it

1. Sign in as **HOD** → *My Timetable* → **Generate & approve timetable**.
2. Sign out, sign in as **asha@college.edu** → *Leaves* → register a leave for an
   upcoming weekday. Substitutes are assigned automatically.
3. Sign back in as **HOD** → *Dashboard* to see absences and coverage, or
   *Substitutions* to reassign or view AI suggestions for uncovered periods,
   or *Fairness* to see substitution balance and export CSV/PDF.

## How requirements map to the code

| Requirement | Where |
| --- | --- |
| 1. Auth & roles | `app/security.py`, `app/routers/auth.py` |
| 2. Timetable generation | `app/services/timetable_generator.py`, `app/routers/timetable.py` |
| 3. Teacher portal | `frontend/src/pages/MyTimetable.jsx` |
| 4. Leave portal | `app/routers/leaves.py`, `frontend/src/pages/Leaves.jsx` |
| 5. Substitution engine | `app/services/substitution_engine.py` |
| 6. AI assistance | `app/services/ai_assist.py` |
| 7. HOD dashboard & reports | `app/routers/dashboard.py`, `frontend/src/pages/{Dashboard,Fairness}.jsx` |
| 8. Notifications | `app/services/notifications.py`, `app/routers/notifications.py` |
| 9. Audit & integrity | `app/services/audit.py`, RBAC via `require_hod` |

## Configuration

Copy `backend/.env.example` to `backend/.env` to override defaults (secret key,
substitution cap, SMTP credentials, database URL). To use PostgreSQL, set
`DATABASE_URL=postgresql+psycopg://user:pass@host/db`.

## Notes & decisions

- Substitutions are **automatic with HOD override** (HOD can reassign any period).
- Weekly substitution cap defaults to **3** per teacher (configurable), applied
  as a soft ranking preference so coverage is never blocked.
- Substitutes are ranked by subject/department match, workload, and fairness;
  the same-department teacher is preferred but any free teacher is eligible.
- Leave quota tracking is intentionally out of scope (per requirements v1).
- The AI layer only *suggests and explains*; final assignment stays rule-based
  and auditable.
