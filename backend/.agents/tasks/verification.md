# Verification — timetable importer clash resolution

Iteration: first (no `review.json` present). Applied all 26 edits from `plan.md`
to the `SCHEDULE` dict in `import_images_timetable.py`. No helpers were changed.
Every edit is a column relocation or day relocation of a `P(...)` row; no period
was dropped and none was added.

## Step 1 — Importer runs with zero clashes

Command (cwd = `backend`):

```
.\.venv\Scripts\python.exe import_images_timetable.py
```

Result:

```
Imported timetable v5: 218 period-slots across 16 classes.
  Per teacher (period-slots incl. both halves of a lab block):
    anjana@college.edu         13
    rajeev@college.edu         16
    hari@college.edu           17
    spurgen@college.edu        21
    meenu@college.edu          16
    joseph@college.edu         21
    soumya@college.edu         18
    andal@college.edu          17
    sameeran@college.edu       15
    sruthi@college.edu         17
    nisha@college.edu          18
    sanjay@college.edu         15
    vipin@college.edu          9
    mani@college.edu           17
  No clashes. Every period placed exactly as transcribed.
```

Success line printed; zero clash lines.

## Step 2 — Per-teacher counts are reasonable vs the grids

Important note on the baseline comparison in `plan.md`: the pre-fix counts
(anjana 13, rajeev 16, hari 15, spurgen 18, meenu 13, joseph 20, soumya 17,
andal 14, sameeran 10, sruthi 14, nisha 16, sanjay 12, vipin 8, mani 11;
185 total) were **artificially low** because the importer SKIPS a period when it
clashes (the `if clash: continue` path never increments `counts`). With 32 clash
lines at baseline, ~33 period-slots were being dropped from the counts. After the
fixes every defined period places, so the counts rise to their true grid values
and the total rises 185 -> 218. This is the correct direction: relocations do not
add periods, they let previously-skipped periods land.

Confirmation that 218 equals exactly what `SCHEDULE` defines (so nothing was
added or lost), counting a `double=True` row as 2 slots and a co-taught lab for
the primary teacher only (the DB stores co-taught labs as ONE row):

```
.\.venv\Scripts\python.exe -c "import import_images_timetable as m; ... sum over SCHEDULE"
total primary-slots: 218
  anjana 13   rajeev 16   hari 17   spurgen 21   meenu 16   joseph 21
  soumya 18   andal 17    sameeran 15  sruthi 17  nisha 18  sanjay 15
  vipin 9     mani 17
```

These equal the importer's printed per-teacher counts exactly, and each matches
the number of cells that teacher has in `TIMETABLE_SOURCE.md` (a double = 2,
co-taught lab counted on the primary). Spot checks against the source grid:

- Anjana: 3 ACN + 1 ACN + 3 BC/BC-Lab + 1 ACN-Lab + Fri double(2) + Sat double(2)
  + Sat BC = 13. Matches.
- Spurgen: 5 lectures + Tue lab(2) + Tue CN(2) + Wed DWDM(1) + Wed lab(2) +
  Wed CN(1) + Wed DSA-Lab(2) + Thu(1) + Fri(2) + Fri(1) + Sat(2) = 21. Matches.
- Mani: NLP-Lab(2) + Python-Lab(2) + Python(1) + 3 lectures + Python(1) +
  PFUC(1) + Python-Lab(2) + Fri(2) + Sat(3) = 17. Matches.

No teacher dropped to a near-zero/implausible count. Vipin (9) is the smallest and
matches his 8-cell grid plus the Tue lab double counting as 2 (6 singles + 1
single-slot Cyber Lab + 1 double = 9).

## Step 3 — DB per-slot conflict check (must be 0 / 0)

Command (cwd = `backend`):

```
.\.venv\Scripts\python.exe -c "from app.database import SessionLocal; from app.models import TimetableEntry; from collections import defaultdict; db=SessionLocal(); es=[e for e in db.query(TimetableEntry).all() if e.is_active]; tt=defaultdict(list); cc=defaultdict(list);
for e in es:
    tt[(e.time_slot_id,e.teacher_id)].append(e.id); cc[(e.time_slot_id,e.class_section_id)].append(e.id)
print('active entries:',len(es)); print('teacher clashes:',sum(1 for v in tt.values() if len(v)>1)); print('class clashes:',sum(1 for v in cc.values() if len(v)>1)); db.close()"
```

Result:

```
active entries: 218
teacher clashes: 0
class clashes: 0
```

## Step 4 — Live server confirmation (port 8010)

The backend was listening on 127.0.0.1:8010. POST form login as
`anjana@college.edu` / `password123`, then GET `/api/timetable/active` with the
returned Bearer token:

```
API active entries: 218
type: list
```

Matches the DB and importer counts (218). The imported data is live.

## Notes / accepted ambiguities

- Item 7 (Sat ACN Lab double): S1 MCA A Sat afternoon had no free adjacent pair
  (Andal AI at c4, Anjana's own BC at c6, Rajeev Python at c7). The ACN-Lab double
  was relocated to the only free adjacent pair for the class, the morning pair
  c0-c1. This is off the MCA afternoon window but keeps both lab periods and drops
  nothing — accepted per the rules (nearest free in-window pair unavailable).
- Item 19/20 (S1 MCA B Mon c5 triple-stack, flagged in the source itself): Nisha
  DSA kept at Mon c5; Sanjay AI relocated to Wed c4; Mani's Python-Lab double
  relocated to Thu c5-c6. All three periods preserved.
- Item 4/26 coordination: Rajeev AI IOT -> Sat c6, Mani Python stays Sat c5,
  Joseph SE -> Sat c7, so S3 MCA GEN Sat holds NOSQL(c3), NLP Lab(c4), Python(c5),
  AI IOT(c6), SE(c7) with no overlap.

All four verification steps pass. No files other than
`import_images_timetable.py` were modified. No commit was made (per task scope).
