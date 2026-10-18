# SCHEDULE clash resolution — faithful relocation of every transcribed period

The change rewrites the `SCHEDULE` dict in `import_images_timetable.py` so the importer places all 218 period-slots with zero teacher/class clashes, down from ~32 clash lines at baseline. Each of the 26 fixes is a single-cell day/column relocation of a `P(...)` row (or a lab double shifted as a unit); no period was deleted and none was added. The approach keeps the stronger of each clashing pair in place (solid lab doubles, multi-day runs, window-correct cells) and shifts the cell most plausibly mis-read one column off into the nearest free in-window slot. I verified cell preservation by mapping every source cell to a SCHEDULE row for all 14 teachers, and the coder's recorded importer/DB evidence shows the success line and 0/0 clashes.

Watch for: one lab double (Mani Python Lab, relocated to Thu c5–c6) straddles the afternoon break, which contradicts the plan's own "same side of a break" rule — but this is **confirmed** to be faithful to the source, whose original Mani Python Lab double at Mon c5 spans the identical c5–c6 columns, so it is not a regression (possible, low severity).

**Verdict**: APPROVED

## High-level view

Every period in `TIMETABLE_SOURCE.md` is preserved. I hand-mapped all 14 teacher grids cell-by-cell to the SCHEDULE rows: each source cell corresponds to exactly one row, with relocations annotated inline and matching the plan's item numbers. No teacher's cell set shrank; the six co-taught labs remain listed once on their primary teacher with the co-teacher wired in, matching the single-listing rule.

The clash resolutions respect the window policy where a free in-window slot existed, and the two documented exceptions (Anjana's Sat ACN-Lab double forced to morning c0–c1, and the Mon c5 triple-stack on S1 MCA B) are the ones the source and plan already flagged as genuine ambiguities. Relocated lab doubles stay adjacent and within the day; the single-period labs (Anjana BC Lab, Vipin Cyber Lab) stayed single.

The evidence in `verification.md` is present and internally consistent: the importer prints "No clashes. Every period placed exactly as transcribed." with 218 slots, and the DB conflict check reports teacher clashes 0 and class clashes 0. The count rise from the plan's 185 baseline to 218 is explained — the baseline was artificially low because clashing periods were skipped (`if clash: continue` never incremented the counter), so 218 reflects every defined period now landing.

Scope is clean: only the SCHEDULE dict changed. No importer helper, model, router, or other backend logic was touched. The frontend edits present in the working tree (`api.js`, `auth.jsx`) belong to earlier steps of the broader request, not this clash-resolution task, and no `app/` file is modified or untracked.

<details>
<summary>Issues (1)</summary>

1. **Break-straddling lab double (informational)** — Mani's relocated Python Lab double sits at Thu c5–c6, spanning the afternoon break, which the plan's stated lab rule discourages; it is faithful to the source (original span was Mon c5–c6, identically straddling), so no action is required, but note it if a future rule enforces same-side-of-break doubles.

</details>

<details>
<summary>Details</summary>

### Every transcribed period is still present (confirmed)

I mapped each cell in `TIMETABLE_SOURCE.md` to a SCHEDULE row for all 14 teachers. Counts line up exactly: Anjana 11 rows (13 slots with two doubles), Rajeev 13, Hari 13, Spurgen 18, Meenu 10 own-rows (co-taught Python/DBMS labs correctly omitted and carried on Hari), Joseph 14, Soumya 13, Andal 14 (the Fri c6 "TDPCL" marked ignore in the source is correctly absent), Sameeran 15, Sruthi 15, Nisha 15, Sanjay 14, Vipin 8, Mani 14. No teacher's cell set dropped. Every relocation carries an inline comment naming the clash it resolves and the plan item, and each traces back to a real source cell:

- Anjana Mon c7 ACN → Tue c5; Wed c6/c7 BC+BC-Lab → Thu c4/c5; Thu/Fri/Sat ACN-Lab doubles shifted as units. All four ACN-Lab blocks and both BC periods survive.
- Joseph's four relocations (Wed/Fri ML, Sat SE, Sat Python) land on distinct free Joseph slots; the Sat trio (Python c5, SE c7) plus Rajeev AI IOT c6 and Mani Python c5 resolve the S3 MCA GEN Sat stack without collision.
- Sruthi, Nisha, Sanjay, Vipin, Sameeran relocations each move a single mis-read cell one column or one day, preserving the period.

Because the importer skips a period on clash (`if clash: continue`), the pre-fix count of 185 understated the true total by the ~33 skipped slots. The post-fix total of 218 is every defined period landing — a count rise is the correct direction for relocation-only edits, and `verification.md` confirms 218 equals what `SCHEDULE` defines (double = 2 slots, co-taught lab on primary only).

### Clash resolutions pick the plausible cell and honor the window policy (confirmed/likely)

Each resolution keeps the cell with corroborating structure — a colored lab double (Rajeev ML Lab Mon c2–c3, Spurgen DWDM Lab Wed c2–c3, Andal Pentest Lab Mon c1–c2, Mani NLP Lab Mon c4–c5), a multi-day subject run (Hari AI DL, Spurgen CN/DSA, Sameeran GE), or a window-correct lecture — and shifts the one-column-off read. Targets stay in the class's window where a free slot existed: S3/MCA cells moved within afternoon cols 4–7 (e.g. Meenu Python Tue/Wed c4→c5, Joseph ML Fri c4→c6), S1/S5 BCA cells within morning cols 0–3 (Vipin DF Mon c2→c0, Nisha DSM Fri c3→c2, Andal Python Theory Sat c3→c0, Soumya Crypto Thu c1→c2).

Two placements leave the window, both pre-flagged as genuine ambiguities rather than arbitrary choices. Anjana's Sat ACN-Lab double had no free adjacent afternoon pair (Andal AI at c4, Anjana's own BC at c6, Rajeev Python at c7), so it went to the only free adjacent pair, morning c0–c1 — off-window but dropping nothing. The S1 MCA B Mon c5 triple-stack (Nisha DSA, Sanjay AI, Mani Python-Lab double) is the overlap the source itself flags; Nisha DSA stays window-correct at Mon c5, Sanjay AI moves to Wed c4, Mani's double to Thu c5–c6, keeping all three.

### Lab double adjacency and the break-straddle note (confirmed)

The three relocated doubles stay adjacent and inside the day. Anjana Fri ACN-Lab → c6–c7 and Sat ACN-Lab → c0–c1 both sit on one side of a break. Mani's Python-Lab double → Thu c5–c6 straddles the afternoon break (c5 = 1:25, c6 = 2:40), which the plan's own rule says a double should not do. This is not introduced by the fix: the source transcribes this same lab as a Mon c5 double, which spans the identical c5–c6 columns, so the relocation preserves the source's column span faithfully. Worth a note if a stricter rule is later enforced, but it changes no period and matches the source.

The two single-period labs stayed single through their moves: Anjana's BC Lab (source Wed c7, "4th hr", last slot) moved to Thu c5 as a single, and Vipin's Cyber Lab remains a single at Mon c7 (last slot). Neither was wrongly promoted to a double.

### Co-taught single-listing preserved (confirmed)

All six co-taught labs remain listed once on the primary with `co=`: Hari+Meenu Python Lab (Mon) and DBMS Lab (Fri) on Hari; Rajeev+Joseph ML Lab (Mon) and DL Lab (Thu) on Rajeev; Joseph+Soumya Python Lab (Mon) and DBMS Lab (Tue) on Joseph. The co-teacher rows carry explanatory comments and do not re-list these labs, so the DB stores each as one entry — consistent with the counting in `verification.md`.

### Evidence quality and scope (confirmed)

`verification.md` is present and records all four checks: importer success line with 218 slots and zero clash lines; a standalone recomputation that 218 equals the SCHEDULE definition; the DB per-slot check returning teacher clashes 0 / class clashes 0; and a live API read of 218 active entries. The evidence is internally consistent and matches the importer source I read, so I did not re-run anything. Only the SCHEDULE dict changed — the importer's helpers, `app/models`, routers, and other backend logic are untouched, and no `app/` file shows as modified or untracked. The frontend diffs in the tree are from earlier steps of the overall request and out of this task's scope.

</details>

<details>
<summary>File map</summary>

- `import_images_timetable.py` — SCHEDULE dict only: 26 period relocations (day/column shifts and lab-double unit moves) resolving all cross-teacher and self-booking clashes. Helpers and import logic unchanged.

Full diff: file is untracked (new), so the entire SCHEDULE dict is the change; reviewed against `TIMETABLE_SOURCE.md` and `.agents/tasks/plan.md`.

</details>
