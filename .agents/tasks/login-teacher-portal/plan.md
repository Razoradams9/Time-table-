# Implementation Plan: Real login + restricted Teacher portal

Mode: no approved design, so design decisions are made here (see "Decisions").
Repo: `c:\Users\razor\OneDrive\Documents\GitHub\Time-table-` (backend `backend\`, frontend `frontend\`).
Do NOT commit. Do NOT run `seed.py`, `seed_once.py`, `import_timetable.py`, `import_images_timetable.py`.
Python: `.\.venv\Scripts\python.exe` with cwd `backend`. Frontend has no lint/test runner; the only build check is `npm run build` (cwd `frontend`).
Backend has no pytest suite (only the `smoke_test.py` script), so verification is a temporary HTTP script against the live server on 8010 (item 11).

## Requirements checklist (from the user brief)

Part A, login
- [ ] A1 Remove auto-login. On load: stored token -> `GET /api/auth/me` -> in; otherwise Login page. Remove `VITE_DEFAULT_EMAIL/PASSWORD` from `api.js`, `auth.jsx`, `frontend\.env.example`; fix README "Using the app" (and DEPLOY.md lines ~96 and ~119, which also describe auto-sign-in).
- [ ] A2 New `pages\Login.jsx` (no Layout): Jain branding (`/jain-logo-light.png`, branding from auth context), email + password, show/hide toggle, inline errors (invalid credentials, disabled account, throttled, server unreachable), loading state, labels, autocomplete (`username`, `current-password`), keyboard/aria friendly, responsive, Jain theme. NO Google login, but leave a clearly marked slot (`.login-alt` container below the form) so a "Sign in with Google" button can be added without redesign.
- [ ] A3 Logout control (user menu in the header) that clears token, resets state, returns to /login.
- [ ] A4 Any 401 on an authenticated call -> clear token, go to Login with "Your session has expired" message. Show backend `detail` on failed login. After login go to the originally requested page (else `/`). All routes protected; unauthenticated users can only see `/login`.
- [ ] A5 Forced password change screen when `must_change_password` (current, new with strength rules shown, confirm) -> `POST /api/auth/change-password`; plus a "Change password" entry in the user menu for everyone. `api.changePassword(current_password, new_password)` already matches `ChangePassword` schema in `backend\app\schemas.py` (fields `current_password`, `new_password`): confirmed, no mismatch.
- [ ] A6 Backend: (a) in-memory throttle 5 failures / 10 min per email+IP -> 429 with message and `Retry-After`, success resets, no new dependency; (b) same message and similar timing for unknown email vs wrong password; (c) `get_current_teacher` rejects inactive accounts (already true, verified by test); (d) Token carries what the frontend needs (already has `access_token, role, teacher_id, name, must_change_password`; verified); startup warning when `secret_key` is the default.

Part B, Teacher portal
- [ ] B1 `TeacherDashboard.jsx` (name welcome, today's classes with substitution/make-up applied, my hours this week via own workload row, upcoming substitutions I cover, my make-ups, quick actions Register leave / View my timetable). Teacher sidebar ONLY: Dashboard, My Timetable, Courses, Leaves, Make-ups, Messages, Help & Support. Visible "Teacher portal" cue. HOD experience unchanged.
- [ ] B2 Teacher timetable page shows only own schedule (+ Adjusted for own periods only); no Regenerate, no teacher/class pickers for other people. Class timetables allowed read-only only for classes they teach.
- [ ] B3 Backend authorization audit, endpoint by endpoint (table below); 403 (not 404/empty) when a teacher asks for something not theirs. HOD behaviour unchanged.
- [ ] B4 Frontend route guards: teacher on HOD URL (`/teachers`, `/substitutions`, `/fairness`) -> redirect to `/`; `Protected` also handles not-logged-in.
- [ ] B5 Update `Help.jsx` (remove auto sign-in text, add log in/out + change password, teacher-accurate wording).
- [ ] V Verification (item 11-13) and cleanup: no leaves/substitutions/compensations/notifications/audit test rows left; 218 timetable entries and 14 accounts unchanged.

## Decisions

1. Teacher "My Timetable" is `/timetable` (existing `TimetableViews.jsx`) in a teacher mode, not `/my-timetable`. Reason: only `TimetableViews` has the Adjusted overlay, so one page serves both requirements. Teachers hitting `/my-timetable` are redirected to `/timetable`. HOD keeps both routes and nav unchanged (the HOD sidebar stays exactly as today).
2. Teacher class access: backend allows `GET /api/timetable/view/class/{id}` only for a class where the teacher leads or co-teaches an active entry (else 403); UI exposes it as a read-only "My classes" tab with a picker listing only those classes. Reason: useful to know co-located classes, no edit controls exist, and the data is already shown on the teacher's own grid.
3. Teacher Adjusted view is own-periods only (teacher subject fixed to self; no "by class" toggle). Backend `compensations/calendar` is limited to the caller's own make-ups for teachers; the substitutions list already scopes to involvement.
4. Courses: teachers get only their own row (`teacher_id` omitted or equal to own; any other id -> 403). The Courses page hides the search/teacher filter for teachers and is titled "My courses".
5. Throttle key is `(email.lower(), client ip)`; `request.client.host` is used (behind Fly/Render proxies the IP may be the proxy's, so the per-email part still limits guessing; documented, no `X-Forwarded-For` trust). Unknown-email path runs `verify_password` against a module-level dummy bcrypt hash for equal timing. Disabled-account 403 is returned only after a correct password (so existence is not leaked by it) and still counts as success for throttle purposes.
6. Forced password change is enforced in the frontend (route gate) only; the backend does not block other endpoints for `must_change_password` users. Recorded as a known limitation, not changed here (would require a global dependency and risks breaking existing flows).
7. Notifications `mark_read` for another teacher's notification changes from 404 to 403 for consistency with "403 not 404".
8. Session expiry mechanism: `api.js` `request()` on a 401 for an authenticated call (not the login call) clears the token and dispatches `window` event `tt:unauthorized`; `AuthProvider` listens, sets `user=null` and `sessionMessage`. Avoids circular imports and router coupling.

## Backend endpoint authorization audit

Source: every file in `backend\app\routers\*.py`, `backend\app\main.py`, `backend\app\security.py` (read in full).
Legend: HOD = `require_hod`; ANY = `get_current_teacher` (any active logged-in user); OWN = ANY + data scoped to caller; PUBLIC = no auth. "FIX" = code change needed.

| # | Route | CURRENT auth | TARGET | Status |
|---|-------|--------------|--------|--------|
| 1 | GET /api/health | PUBLIC | PUBLIC | ok |
| 2 | GET /api/branding | PUBLIC | PUBLIC (Login page needs it) | ok |
| 3 | POST /api/auth/login | PUBLIC, no throttle, timing differs for unknown email | PUBLIC + throttle + uniform error/timing | **FIX** (item 1) |
| 4 | GET /api/auth/me | ANY | ANY | ok |
| 5 | POST /api/auth/change-password | ANY (own) | ANY (own) | ok |
| 6 | GET /api/accounts | HOD | HOD | ok |
| 7 | POST /api/accounts | HOD | HOD | ok |
| 8 | PATCH /api/accounts/{id} | HOD | HOD | ok |
| 9 | POST /api/accounts/{id}/reset-password | HOD | HOD | ok |
| 10 | GET /api/reference/time-slots | ANY | ANY | ok |
| 11 | GET /api/reference/teachers | HOD | HOD | ok |
| 12 | GET /api/reference/subjects | HOD | HOD | ok |
| 13 | GET /api/reference/classes | HOD | HOD | ok |
| 14 | GET /api/reference/rooms | HOD | HOD | ok |
| 15 | GET /api/reference/departments | HOD | HOD | ok |
| 16 | GET /api/timetable/view/options | ANY, returns ALL teachers and classes | OWN: teacher gets only self + classes they teach; HOD all | **FIX** |
| 17 | GET /api/timetable/view/teacher/{id} | ANY, any id | OWN: teacher id must equal own else 403; HOD any | **FIX** |
| 18 | GET /api/timetable/view/class/{id} | ANY, any class | teacher only for classes they teach else 403; HOD any | **FIX** |
| 19 | POST /api/timetable/generate | HOD | HOD | ok |
| 20 | POST /api/timetable/approve/{version} | HOD | HOD | ok |
| 21 | GET /api/timetable/versions | HOD | HOD | ok |
| 22 | GET /api/timetable/active | ANY, teacher already filtered to own | OWN | ok |
| 23 | GET /api/timetable/version/{version} | HOD | HOD | ok |
| 24 | POST /api/leaves | ANY (leave created for caller only) | OWN | ok |
| 25 | GET /api/leaves | ANY, teacher filtered to own | OWN (HOD all) | ok |
| 26 | DELETE /api/leaves/{id} | ANY, owner or HOD else 403 | OWN or HOD | ok |
| 27 | GET /api/substitutions | ANY, teacher filtered to involved subs | OWN (HOD all) | ok |
| 28 | GET /api/substitutions/{id}/candidates | HOD | HOD | ok |
| 29 | GET /api/substitutions/{id}/suggestions | HOD | HOD | ok |
| 30 | GET /api/substitutions/{id}/explanation | ANY, any substitution | teacher only if absent or substitute else 403; HOD any | **FIX** |
| 31 | POST /api/substitutions/{id}/assign | HOD | HOD | ok |
| 32 | GET /api/dashboard/overview | HOD | HOD | ok |
| 33 | GET /api/dashboard/activity | HOD | HOD | ok |
| 34 | GET /api/dashboard/summary | HOD | HOD | ok |
| 35 | GET /api/dashboard/fairness | HOD | HOD | ok |
| 36 | GET /api/dashboard/workload | ANY; teacher forced to self, other `teacher_id` -> 403 | OWN (HOD any) | ok (re-verify by test) |
| 37 | GET /api/dashboard/leave-history/{teacher_id} | HOD | HOD | ok |
| 38 | GET /api/dashboard/export/fairness.csv | HOD | HOD | ok |
| 39 | GET /api/dashboard/export/fairness.pdf | HOD | HOD | ok |
| 40 | GET /api/notifications | ANY, own only | OWN | ok |
| 41 | GET /api/notifications/unread-count | ANY, own only | OWN | ok |
| 42 | POST /api/notifications/{id}/read | ANY, other's -> 404 | OWN; other's -> 403 | **FIX** (minor) |
| 43 | POST /api/notifications/read-all | ANY, own only | OWN | ok |
| 44 | GET /api/courses | ANY, returns ALL teachers; `teacher_id` unrestricted | OWN: teacher forced to self, other id -> 403; HOD all | **FIX** |
| 45 | GET /api/compensations | ANY; teacher's `teacher_id` param silently ignored | OWN; other `teacher_id` -> 403; HOD any | **FIX** |
| 46 | GET /api/compensations/summary | same as 45 | same as 45 | **FIX** |
| 47 | GET /api/compensations/calendar | ANY, returns ALL teachers' make-ups (names, classes) | OWN: teacher sees only own; HOD all | **FIX** |
| 48 | POST /api/compensations/backfill | HOD | HOD | ok |
| 49 | GET /api/compensations/{id}/suggestions | ANY via `_get` (owner or HOD, else 403) | OWN or HOD | ok |
| 50 | POST /api/compensations/{id}/confirm | owner or HOD | OWN or HOD | ok |
| 51 | POST /api/compensations/{id}/reschedule | owner or HOD | OWN or HOD | ok |
| 52 | POST /api/compensations/{id}/complete | owner or HOD | OWN or HOD | ok |
| 53 | POST /api/compensations/{id}/cancel | HOD (via `_get(hod_only=True)`) | HOD | ok |
| 54 | POST /api/compensations/{id}/repropose | owner or HOD | OWN or HOD | ok |

Count: 54 route handlers (plus FastAPI `/docs`, `/openapi.json`, `/redoc`, left public).
**Endpoints needing fixes: 10** = 8 authorization leaks (#16, 17, 18, 30, 44, 45, 46, 47) + 1 minor 404->403 consistency (#42) + 1 login hardening (#3). `security.py` itself needs no authorization change (`get_current_teacher` already rejects `is_active == False`, `require_hod` is correct); it only gets a shared helper (see item 2).

## Ordered tasks

Order by dependency: backend first (items 1-3), then frontend plumbing (4-5), screens (6-9), docs (10), verification (11-13).

- [ ] 1. Login hardening: throttle, uniform failure, secret-key warning.
      Create `backend\app\services\login_throttle.py`: module-level `threading.Lock`, `dict[tuple[str,str], deque[float]]`; functions `retry_after(key) -> int` (0 if allowed; prunes entries older than window), `record_failure(key)`, `reset(key)`. Constants `login_max_attempts: int = 5` and `login_window_seconds: int = 600` added to `Settings` in `backend\app\config.py`.
      Rewrite `login()` in `backend\app\routers/auth.py`: add `request: Request`; `email = form.username.strip().lower()`; key = `(email, request.client.host)`; if `retry_after>0` raise `HTTPException(429, "Too many failed sign-in attempts. Try again in N minute(s).", headers={"Retry-After": ...})`; look up with `func.lower(Teacher.email) == email`; when teacher is None call `verify_password(form.password, _DUMMY_HASH)` (`_DUMMY_HASH = hash_password("not-a-real-password")` computed once at import) so timing matches; on failure `record_failure` and raise the SAME 401 `"Invalid email or password."`; on success `reset(key)`; if inactive raise 403 `"This account has been disabled. Contact your HOD."`. Token response unchanged.
      In `backend\app\main.py` startup, `logging.getLogger(__name__).warning(...)` when `settings.secret_key` equals the default string in `config.py` ("SECRET_KEY is still the insecure default; set SECRET_KEY in backend/.env before deploying"). No behaviour change.
      Files: `backend\app\services\login_throttle.py` (new), `backend\app\config.py`, `backend\app\routers\auth.py`, `backend\app\main.py`
      Verify: from `backend`, `.\.venv\Scripts\python.exe -c "import app.main"` imports cleanly; restart server (item 3) then POST 6 bad logins for `throwaway@college.edu` via form-encoded request and see 401 x5 then 429 with `Retry-After`, while `nisha@college.edu` still logs in 200 (full script in item 11).

- [ ] 2. Backend authorization fixes (8 leaks + notifications).
      `backend\app\security.py`: add `def is_hod(user) -> bool` and `def forbid(detail="You do not have access to this data.")` that raises 403 (small shared helpers; keep `require_hod` as is).
      `backend\app\routers\timetable.py`:
        - `view_options`: if not HOD, `teachers=[current]`, `classes` = `ClassSection` rows whose id is in `select(TimetableEntry.class_section_id).where(is_active, (teacher_id==current.id)|(co_teacher_id==current.id))`, ordered by name.
        - `teacher_view`: if not HOD and `teacher_id != current.id` -> 403 `"You can only view your own timetable."`.
        - `class_view`: if not HOD and the teacher has no active entry (lead or co) in that class -> 403 `"You can only view classes you teach."`.
      `backend\app\routers\substitutions.py` `explanation`: after the 404 check, if not HOD and `current.id not in (sub.absent_teacher_id, sub.substitute_teacher_id)` -> 403.
      `backend\app\routers\courses.py` `list_courses`: replace `_` with `current`; if not HOD: `if teacher_id not in (None, current.id): 403`; `teacher_id = current.id`. Update module docstring (no longer "every logged-in user may read all").
      `backend\app\routers\compensations.py`: in `_visible_query` for non-HOD raise 403 when `teacher_id is not None and teacher_id != current.id`; in `calendar` add `.where(Compensation.teacher_id == current.id)` for non-HOD; update the module docstring about the calendar.
      `backend\app\routers\notifications.py` `mark_read`: 404 if notification missing, 403 if it belongs to someone else.
      HOD behaviour must stay byte-for-byte identical (all new checks are `if not HOD`).
      Files: `backend\app\security.py`, `backend\app\routers\timetable.py`, `backend\app\routers\substitutions.py`, `backend\app\routers\courses.py`, `backend\app\routers\compensations.py`, `backend\app\routers\notifications.py`
      Verify: `.\.venv\Scripts\python.exe -c "import app.main"` from `backend` succeeds; full authorization matrix script in item 11.

- [ ] 3. Restart the backend so items 1-2 are live.
      `Get-NetTCPConnection -LocalPort 8010 -State Listen` -> `Stop-Process -Id <OwningProcess>`; from `backend` start in background `.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010`. Leave it running at the end.
      Files: none
      Verify: `Invoke-RestMethod http://127.0.0.1:8010/api/health` returns `status ok`; the server log shows the secret-key warning if `.env` has no real key.

- [ ] 4. Frontend API/auth plumbing (depends on 1).
      `frontend\src\api.js`: delete `defaultEmail/defaultPassword`; `login(email, password)` required args; in `request()` wrap `fetch` in try/catch -> on `TypeError` throw `Error("Cannot reach the server. Check your connection and try again.")`; on `res.status === 401 && auth && getToken()` call `setToken(null)` and `window.dispatchEvent(new Event("tt:unauthorized"))` before throwing. Keep `changePassword(current_password, new_password)` as is.
      `frontend\src\auth.jsx`: `boot()` = branding fetch, then if `getToken()` try `api.me()` (on failure `setToken(null)`), no auto-login; add state `sessionMessage`; `useEffect` listener for `tt:unauthorized` -> `setUser(null)`, `setSessionMessage("Your session has expired. Please sign in again.")`; `login(email, password)` clears `sessionMessage`, awaits `api.login`, then `api.me()` and sets user (normalized); `logout()` clears token, user, message; keep `refreshUser`; expose `sessionMessage`, `clearSessionMessage`.
      `frontend\.env.example`: remove the 3 auto-login lines/comments.
      Files: `frontend\src\api.js`, `frontend\src\auth.jsx`, `frontend\.env.example`
      Verify: `npm run build` in `frontend` passes.

- [ ] 5. Routing and guards in `frontend\src\App.jsx` (depends on 4; screens in 6-8 must exist, so create stub imports in the same commit-free change set or do items 6-8 first then wire this).
      Rewrite `Protected({ hodOnly })`: no user -> `<Navigate to="/login" replace state={{ from: location }} />`; `hodOnly && role !== "HOD"` -> `<Navigate to="/" replace />`. `App`: while `loading` show spinner; routes: `/login` (if user then `<Navigate to={from || "/"}>`, else `<Login/>`); if `user.must_change_password` render only `/change-password` (standalone `<ChangePassword forced />`) and redirect everything else to it; otherwise Layout routes as today with `/` -> `isHod ? <Dashboard/> : <TeacherDashboard/>`, `/change-password` inside Layout, `/my-timetable` -> HOD: `<MyTimetable/>`, teacher: `<Navigate to="/timetable" replace/>`. Wrap `/teachers`, `/substitutions`, `/fairness` and (HOD-only) `/my-timetable` in `<Protected hodOnly>`; remove the "Can't reach the server" retry screen (Login shows that error).
      Files: `frontend\src\App.jsx`
      Verify: `npm run build` passes.

- [ ] 6. Login page and change-password screen.
      Create `frontend\src\pages\Login.jsx` (uses `useAuth().login`, `useLocation().state?.from`, `sessionMessage`, branding): form with `<label htmlFor>` + `autoComplete="username"` / `"current-password"`, `type="email"` with `required`, show/hide button (`aria-pressed`, `aria-label="Show password"/"Hide password"`), submit disabled + "Signing in…" while loading, error block `role="alert"` (shows backend `detail`, "session expired" notice as `role="status"`), focus moves to the first field / error; a `<div className="login-alt">` placeholder comment for the future Google button; footer with institution/department from branding. Navigate to `from` or `/` on success.
      Create `frontend\src\pages\ChangePassword.jsx` (prop `forced`): fields current / new / confirm (`autoComplete="current-password"`, `"new-password"`), live checklist of the backend rules (>=8 characters, a letter, a number, differs from current, confirm matches), submit calls `api.changePassword`, on success `await refreshUser()` then `navigate("/")`; when `forced` render standalone card with "Sign out" link and no sidebar; otherwise inside Layout with PageHeader. Show backend `detail` on error (e.g. "Current password is incorrect.").
      Append styles to `frontend\src\styles.css` (`.login-shell`, `.login-card`, `.pw-field`, `.pw-toggle`, `.pw-rules`, `.login-alt`) reusing CSS variables at the top of the file (navy `#012549`, orange `#ff7a00`), mobile breakpoint at ~480px.
      Files: `frontend\src\pages\Login.jsx` (new), `frontend\src\pages\ChangePassword.jsx` (new), `frontend\src\styles.css`
      Verify: `npm run build` passes; later browser checks in item 12.

- [ ] 7. Layout: role-specific navigation, user menu, teacher cue.
      `frontend\src\components\Layout.jsx`: HOD nav list unchanged. Add `teacherNav` = Dashboard `/`, My Timetable `/timetable`, Courses `/courses`, Leaves `/leaves`, Make-ups `/compensations`, Messages `/notifications`; bottom nav Help & Support. Choose list by `isHod`. Replace the static user chip with a button-driven menu (`aria-haspopup="menu"`, `aria-expanded`, closes on Esc/outside click/route change) with items "Change password" (`<Link to="/change-password">`) and "Log out" (`logout()` then `navigate("/login")`; use `icons.logout`). Add class `teacher-portal` on `.app-shell` for teachers, show a "Teacher portal" pill next to the product label in the header and in the sidebar top; keep `Administrator` label for HOD. On mobile keep the chip operable (name hidden is fine, menu still reachable).
      Add the needed styles (`.user-menu`, `.user-menu-list`, `.portal-pill`, `.teacher-portal .side-link.active` accent) to `frontend\src\styles.css`.
      Files: `frontend\src\components\Layout.jsx`, `frontend\src\styles.css`
      Verify: `npm run build` passes.

- [ ] 8. Teacher dashboard and Dashboard cleanup.
      Create `frontend\src\pages\TeacherDashboard.jsx`: loads in parallel `api.activeTimetable()` (own entries), `api.timeSlots()`, `api.substitutions()` (own involvement), `api.compensations({ status: "PROPOSED,SCHEDULED" })`, `api.compensationSummary()`; renders welcome card (reuse `.welcome-card`, greeting by `user.name`, date via `localISO` from `dateUtils.js`, NOT `toISOString` which is UTC), "Today's classes" table (own entries for today's weekday; rows where an ASSIGNED substitution on today's date has me as absent show "Covered by X" pill; rows where I am the substitute are added with a "Covering" pill; make-ups dated today added with a "Make-up" pill), `<MyHoursCard />` (already requests only own workload), "Upcoming substitutions I'm covering" (`substitute_teacher_id === user.teacher_id`, `override_date >= today`), "My make-up classes" (fields per `CompensationOut` in `backend\app\schemas.py` line ~318; read it first), quick actions (Register leave -> `/leaves`, View my timetable -> `/timetable`) reusing `.quick-grid`/`.quick-action`. Skeleton loaders as in `Dashboard.jsx`; show errors in `.error`.
      Edit `frontend\src\pages\Dashboard.jsx` to be HOD-only: remove `!isHod` "Your day" card and the non-HOD branches (keep `isHod` removal minimal and behaviour identical for HOD).
      Files: `frontend\src\pages\TeacherDashboard.jsx` (new), `frontend\src\pages\Dashboard.jsx`, `frontend\src\styles.css` (only if new classes are needed)
      Verify: `npm run build` passes.

- [ ] 9. Teacher-restricted timetable, courses, make-ups pages.
      `frontend\src\pages\TimetableViews.jsx`: for `!isHod`: tabs become "My schedule" (teacher mode, `teacherId` fixed to `user.teacher_id`, no teacher `<select>`), "My classes" (stream mode with `options.classes`, read-only, class picker only), "Adjusted" (teacher subject fixed to self: hide the "View adjusted schedule by" toggle and force `adjSubject="teacher"`); title "My Timetable"; never render Regenerate (already `isHod`-gated, keep) and drop the HOD "Generate on the Dashboard" hint for teachers. Because `/view/options` now returns only self for teachers, default selection logic still works. HOD UI must remain identical.
      `frontend\src\pages\Courses.jsx`: for teachers hide search and teacher filter, title "My courses", subtitle "Your courses, taken from the active timetable." (use `useAuth`).
      `frontend\src\pages\Compensations.jsx`: title/subtitle "My make-ups" for teachers (the HOD-only teacher filter and backfill are already gated by `isHod`, lines ~85-184); verify no HOD-only button (Cancel, Backfill) renders for teachers.
      `frontend\src\pages\MyTimetable.jsx`: leave as the HOD master view; remove the now-dead `!isHod` branches only if trivial, otherwise leave.
      Files: `frontend\src\pages\TimetableViews.jsx`, `frontend\src\pages\Courses.jsx`, `frontend\src\pages\Compensations.jsx`, `frontend\src\pages\MyTimetable.jsx` (optional cleanup)
      Verify: `npm run build` passes.

- [ ] 10. Docs and help text.
      `frontend\src\pages\Help.jsx`: replace the FAQ "I can't reach the server" answer (currently says the app signs in automatically) with sign-in/session guidance; add FAQs "How do I sign in and out?" and "How do I change my password?" (menu in the header; first login forces a change; rules: 8+ characters with a letter and a number; HOD can reset it); change "How do I view my timetable?" to match teacher UI (My schedule / My classes / Adjusted) and keep the HOD wording (`hod: true` variant or role-aware text); fix the Courses FAQ ("Every teacher's courses" is HOD-only now) and the workload FAQ; make-ups FAQ: say "Open Make-ups" for teachers; TOPICS "Timetable"/"Courses" body text role-aware. The help page already filters with `t.hod`/`f.hod`; add an optional `teacher: true` flag if separate wording is needed.
      `README.md` "Using the app" (lines ~53-69): replace with: sign in at `/login`, HOD `anjana@college.edu`, teachers `<name>@college.edu`, seeded password `password123` (change it on first use), forced change flow, logout, teacher portal vs HOD features; delete the "default credentials ship in the frontend" warning; mention throttling and `SECRET_KEY`.
      `DEPLOY.md` lines ~96 and ~119: remove "frontend auto-signs in ... no login screen ... anyone gets admin access".
      Files: `frontend\src\pages\Help.jsx`, `README.md`, `DEPLOY.md`
      Verify: `npm run build` passes; `Select-String -Path README.md,DEPLOY.md,frontend\src\pages\Help.jsx,frontend\.env.example -Pattern 'auto-sign|signs in automatically|VITE_DEFAULT|no login screen'` returns nothing (sanity check only; real verification is items 11-13).

- [ ] 11. Backend authorization test (temporary script, then delete).
      Create `backend\_tmp_authz_test.py` (stdlib `urllib`/`json` only; talks to `http://127.0.0.1:8010`). Steps:
        a. Log in as HOD `anjana@college.edu`, teachers `nisha@college.edu`, `spurgen@college.edu` (all `password123`). Get ids from `GET /api/auth/me`.
        b. Iterate `app.routes` (import `app.main`, filter `APIRoute`), build concrete URLs (path params 1 or a real id; dates `?start=&end=&on=`), call each with HOD token, teacher token, no token; print table `method path | HOD | teacher | anon`. Mutating routes (POST/PATCH/DELETE) are only exercised where safe: call HOD-only POSTs (`/accounts`, `/timetable/generate`, `/timetable/approve/1`, `/compensations/backfill`, `/accounts/{id}/reset-password`) ONLY with the teacher token and expect 403; DO NOT call them with the HOD token (generate/approve would alter the timetable).
        c. Assert: teacher gets 403 on all HOD-only routes in the table above; 403 for `/dashboard/workload?teacher_id=<other>`, `/courses?teacher_id=<other>`, `/compensations?teacher_id=<other>`, `/compensations/summary?teacher_id=<other>`, `/timetable/view/teacher/<other>`, `/timetable/view/class/<class the teacher does not teach>`; 200 for own workload/courses/compensations/timetable and own classes; `/timetable/view/options` for a teacher returns exactly one teacher (self) and only classes they teach; `/timetable/active` for a teacher returns only entries where they are lead/co; `/compensations/calendar?on=` contains only own `teacher_id`; no token -> 401 on every `/api/*` route except health, branding, login.
        d. Disabled-account: HOD `PATCH /api/accounts/<id>` `{"is_active": false}` on a non-demo target teacher (use `mani@college.edu`, log in first to get its token, then disable, expect that existing token gets 401 and a fresh login gets 403 "disabled"), then ALWAYS re-enable in a `finally` block and confirm `is_active` true afterwards.
        e. Throttle: 5 wrong logins for `throwaway-xyz@college.edu` -> 401 x5 then 429 with `Retry-After`; unknown email and wrong-password messages are identical; a legit `nisha@college.edu` login still returns 200 immediately afterwards; successful login resets the counter (after 4 failures + a success for a real account, 5 more failures needed to trigger 429).
        f. Create a throwaway leave as `nisha` (a future weekday that has a nisha class), confirm `GET /api/substitutions` as nisha shows only involved rows, that the explanation endpoint returns 403 for a substitution she is not part of (use HOD token to find one covering another teacher, or create a leave as `spurgen` and check nisha gets 403 on spurgen's substitution explanation unless she is the substitute), that the substitute teacher sees it and compensations appear for nisha; then cancel both leaves via `DELETE /api/leaves/{id}`.
        g. HOD regression: `/api/timetable/active` length == 218; `/api/accounts` length == 14; `/api/dashboard/workload`, `/api/courses`, `/api/compensations`, `/api/dashboard/overview` return 200.
      After the run, clean up test data with a short backend script via SQLAlchemy using `app.database.SessionLocal` (check `backend\app\database.py` for the real name): delete `Compensation`, `Substitution`, `LeavePeriod`, `Leave`, `Notification` rows created during the test and `AuditLog` rows with id greater than the max id recorded BEFORE the test (record max ids at start). Confirm `substitutions`, `leaves`, `compensations` tables have 0 rows (as they did before testing), timetable still 218 active entries, 14 teachers, all `is_active` true and `must_change_password` unchanged, and `hashed_password` of every account unchanged (compare a hash snapshot taken before/after). Delete the temp script(s).
      Files: `backend\_tmp_authz_test.py` (temporary, deleted at the end)
      Verify: script exits 0 and prints the table; every assertion passes; cleanup query shows 0 rows in `substitutions`, `leaves`, `compensations`.

- [ ] 12. Frontend verification.
      Run `npm run build` in `frontend`, confirm success, then delete `frontend\dist`. Ensure Vite is running on 5173 (start `npm run dev` in background in `frontend` if not). If a browser tool is available, open `http://localhost:5173` and: clear localStorage -> Login appears (no Layout); wrong password shows the error; HOD (`anjana@college.edu`) sees full nav and Dashboard, user menu -> Log out returns to Login; teacher `nisha@college.edu` sees only the 7 teacher nav items + "Teacher portal" cue and Teacher Dashboard; typing `/teachers`, `/substitutions`, `/fairness`, `/my-timetable` as teacher redirects to `/`; deep link `/leaves` while logged out -> Login -> back to `/leaves`; delete the token in devtools and click any page -> redirected to Login with "session expired"; 429 message after repeated bad logins (use a throwaway email); forced change flow: HOD `PATCH`-free method: use `POST /api/accounts/<mani id>/reset-password` as HOD (throwaway account `mani@college.edu`), sign in with the temp password, change password to a temp value, then change it BACK to `password123` through the UI/API and confirm `must_change_password` false and login with `password123` works (this restores the original state; a bcrypt rehash is unavoidable, so note it); viewport ~390px for Login, teacher dashboard and sidebar; take screenshots. If no browser tool exists, say so and exercise the same flows through `http://localhost:5173/api/...` (proves the Vite proxy) and list what could not be verified visually.
      Files: none (delete `frontend\dist` afterwards)
      Verify: `npm run build` exits 0; flows above behave as described; screenshots captured or limitation stated.

- [ ] 13. Final cleanup and state check.
      Confirm: backend (8010) and Vite (5173) running; `git status` shows only intended files (no `dist`, no temp scripts, no `.db` changes beyond test rows already removed); `substitutions`, `leaves`, `compensations`, `notifications` hold no test rows (notifications table should be as before the test; if it had rows before, only delete ones created during the test); nothing committed.
      Files: none
      Verify: `git status --short` lists only the files in the table below; DB counts match item 11 expectations.

## Files to create / modify

Backend
- New: `backend\app\services\login_throttle.py`
- Modify: `backend\app\config.py`, `backend\app\main.py`, `backend\app\security.py`, `backend\app\routers\auth.py`, `backend\app\routers\timetable.py`, `backend\app\routers\substitutions.py`, `backend\app\routers\courses.py`, `backend\app\routers\compensations.py`, `backend\app\routers\notifications.py`
- Temporary (deleted): `backend\_tmp_authz_test.py`

Frontend
- New: `frontend\src\pages\Login.jsx`, `frontend\src\pages\ChangePassword.jsx`, `frontend\src\pages\TeacherDashboard.jsx`
- Modify: `frontend\src\api.js`, `frontend\src\auth.jsx`, `frontend\src\App.jsx`, `frontend\src\components\Layout.jsx`, `frontend\src\pages\Dashboard.jsx`, `frontend\src\pages\TimetableViews.jsx`, `frontend\src\pages\Courses.jsx`, `frontend\src\pages\Compensations.jsx`, `frontend\src\pages\Help.jsx`, `frontend\src\styles.css`, `frontend\.env.example`
- Optional: `frontend\src\pages\MyTimetable.jsx` (dead teacher branches)

Docs: `README.md`, `DEPLOY.md`

## Notes and gaps

- The working tree already has uncommitted changes in many of these files (`git status` shows `api.js`, `App.jsx`, `Layout.jsx`, `Dashboard.jsx`, `TimetableViews.jsx`, `Help.jsx`, `styles.css`, `dashboard.py`, `leaves.py`, `substitutions.py`, `main.py` modified, and `courses.py`, `compensations.py` untracked). Read the current file contents before editing; do not revert them.
- `Classes.jsx` is not routed anywhere; leave it.
- Password hash of seeded accounts must be unchanged at the end; any account used for the forced-change test ends with a different bcrypt salt/hash for the same `password123`, which is acceptable and should be reported.
- Existing `.agents\tasks\plan.md` belongs to an earlier task; do not touch it.
