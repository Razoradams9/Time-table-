# Implementation Plan — Resolve all timetable import clashes

Goal: make `import_images_timetable.py` import with ZERO clashes while keeping every
period from `TIMETABLE_SOURCE.md` present (relocate, never drop). Only the `SCHEDULE`
dict in `import_images_timetable.py` changes.

## Context discovered during exploration

- Column→period mapping: `COL_TO_PIDX = [0,1,3,4,5,6,8,9]`. The clash output prints
  `TimeSlot.period_index`, not grid columns. Inverse map (period_index → grid col):
  `{0:0, 1:1, 3:2, 4:3, 5:4, 6:5, 8:6, 9:7}`.
- The `P(d, p, ...)` rows store the GRID COLUMN ordinal (0..7) in the `p` field; the
  importer converts column→period_index at insert time. So every edit below is
  expressed as a grid-column change to a `P(...)` row.
- Breaks sit between col1/col2 and col5/col6. A `double=True` block must occupy two
  adjacent columns on the same side of a break and must not run past col7.
- Window policy: S1 & S5 BCA → morning cols 0–3; S3 (any) and all MCA → afternoon
  cols 4–7. Used below to pick relocation targets when a grid is ambiguous.
- Build/verify command (run from `backend`, venv): `.\.venv\Scripts\python.exe import_images_timetable.py`
  Expected success line: `No clashes. Every period placed exactly as transcribed.`
- Baseline before fixes: 185 period-slots across 16 classes, 32 clash/issue lines
  (~26 distinct double-bookings; some clashes print one line per overlapping period).

## Clash inventory (grid-column coordinates)

Each item below is one distinct conflict. "Keep" = the cell that is well-supported by
the grid (solid lab block, window-correct, or corroborated elsewhere). "Move" = the
cell most plausibly transcribed one column off, relocated to the nearest free in-window
slot that is empty for BOTH the class and the moved teacher (verified against the full
per-class and per-teacher occupancy dumps built during exploration).

---

- [ ] 1. Fix S3 MCA CS Wed overlap (Anjana BC/BC Lab vs Hari DL Lab).
      Clash: `S3 MCA CS d2 p8/p9` (two lines = the two halves of one overlap) — Anjana Wed c6 BC
      + c7 BC Lab collide with Hari's solid DL Lab double at Wed c6–c7. Hari's colored double
      block is the strong cell; keep it. Anjana's Wed c6 BC and c7 BC Lab are the mis-reads.
      S3 MCA CS Wed has no free afternoon slot before the lab (c4 = Anjana's own kept BC, c5 =
      Hari AI DL). S3 MCA CS Thursday is entirely empty, and after item 2 moves Anjana's Thu
      ACN Lab off c4 (to c6), Anjana's Thu c4/c5 are free. Relocate the pair to Thursday:
      `P(WED,6,"S3 MCA CS","BC")` → `P(THU,4,...)` and
      `P(WED,7,"S3 MCA CS","BC Lab",lab="DIGI")` → `P(THU,5,...)`.
      Keeps both BC periods and the single-period BC Lab; clears Hari's lab. VERIFIED by simulation.
      NOTE: in code these rows use grid-col values, so they read `P(WED,6,...BC)` and
      `P(WED,7,...BC Lab)`. Anjana also has `P(WED,4,...BC)` (grid c4) — that one does NOT clash;
      keep it unchanged.
      Files: `import_images_timetable.py` (anjana `P(WED,6,...BC)` and `P(WED,7,...BC Lab)` rows).
      SEQUENCING: depends on item 2 freeing Anjana Thu c4/c5. Apply item 2's Thu-ACN-Lab move too.
      Verify: re-run importer; the two `S3 MCA CS d2 p8/p9` lines are gone and S3 MCA CS Thu shows BC + BC Lab.

- [ ] 2. Fix S1 MCA A Mon/Thu/Fri/Sat overlaps (Anjana ACN/ACN-Lab vs Spurgen DSA).
      Clashes: `S1 MCA A d0 p5` (Mon c4: Anjana ACN vs Spurgen DSA), `d3 p5` (Thu c4:
      Anjana ACN Lab vs Spurgen DSA), `d4 p5` (Fri c4: Anjana ACN Lab vs Spurgen DSA Lab),
      `d5 p5` (Sat c4: Anjana ACN Lab vs Andal AI — see item 7).
      Root cause: Anjana's S1 MCA A ACN/ACN-Lab cells are transcribed at grid c4, but
      Spurgen owns S1 MCA A DSA at c4 on Mon/Thu/Fri (solid, corroborated by DSA Lab
      doubles). Spurgen is the stronger cell. Shift Anjana's conflicting S1 MCA A cells
      one column right into the free afternoon slot:
        - Mon: `P(MON,4,"S1 MCA A","ACN")` c4→c5 (class Mon c5 free; Anjana Mon c5 free). The
          existing Mon c6/c7 ACN entries stay.
        - Thu: `P(THU,4,"S1 MCA A","ACN Lab",lab="ADMIN")` c4→c5 (single lab; class Thu c5 is
          taken by Andal AI — see item 6 which moves Andal; sequence item 6 first, then c5 is free).
          If still blocked, use Thu c6 (class+Anjana free). Prefer c6 to stay clear of Andal.
          DECISION: move Thu ACN Lab c4→c6 (class Thu c6 free, Anjana Thu c6 free).
        - Fri: Anjana Fri ACN Lab is a double at c4–c5; Spurgen DSA Lab sits at c4. Move Anjana's
          Fri ACN-Lab double c4→c6 is blocked (would be c6–c7, class Fri c6/c7 free, Anjana free) — OK.
          Change `P(FRI,4,"S1 MCA A","ACN Lab",lab="ADMIN")` and `P(FRI,5,...)` to a single
          double at c6: replace the two Fri rows with `P(FRI,6,"S1 MCA A","ACN Lab",lab="ADMIN",double=True)`.
      Files: `import_images_timetable.py` (anjana Mon/Thu/Fri ACN rows).
      Verify: re-run importer; `S1 MCA A d0 p5`, `d3 p5`, `d4 p5` lines gone.

- [ ] 3. Fix S3 BCA CS Tue + Wed overlaps (Meenu Python vs Hari DBMS / Spurgen CN).
      Clashes: `S3 BCA CS d1 p5` (Tue c4: Hari DBMS vs Meenu Python) and
      `S3 BCA CS d2 p5` (Wed c4: Meenu Python vs — class Wed c4 also holds Meenu Python,
      but the clash is Spurgen CN at Wed c4). Hari DBMS (Tue c4) and Spurgen CN (Wed c4)
      are corroborated (Hari has a DBMS cluster, Spurgen has a CN cluster). Meenu's two
      S3 BCA CS Python cells at c4 are the mis-reads. S3 BCA CS afternoon free slots:
      Tue c5 (free for class and Meenu), Wed c5 (free for class and Meenu).
      Edit: `P(TUE,4,"S3 BCA CS","Python")` c4→c5; `P(WED,4,"S3 BCA CS","Python")` c4→c5.
      Files: `import_images_timetable.py` (meenu Tue/Wed Python rows).
      Verify: re-run importer; both `S3 BCA CS d1 p5` and `d2 p5` lines gone.

- [ ] 4. Fix S3 MCA GEN Sat overlap (Rajeev AI IOT vs Meenu NOSQL DB).
      Clash: `S3 MCA GEN d5 p4` (Sat c3: Rajeev AI IOT vs Meenu NOSQL DB). Sat c3 is a
      morning column; S3 MCA GEN is an afternoon class, so BOTH cells are slightly off, but
      Rajeev's Sat AI IOT is his only Sat lecture and Meenu's Sat NOSQL DB is corroborated
      by her NOSQL cluster. Keep Meenu NOSQL DB at c3. Relocate Rajeev AI IOT; Sat c4 is taken
      by Joseph ML and c5 by Mani Python, so the free class+teacher slot is c6. Edit:
      `P(SAT,3,"S3 MCA GEN","AI IOT")` c3→c6. VERIFIED by simulation (coordinated with item 26,
      which places Joseph SE at c7 so the two do not collide).
      Files: `import_images_timetable.py` (rajeev Sat AI IOT row).
      Verify: re-run importer; `S3 MCA GEN d5 p4` line gone.

- [ ] 5. Fix S3 MCA CS Fri overlap (Hari AI DL vs Joseph ML).
      Clash: `S3 MCA CS d4 p5` (Fri c4: Hari AI DL vs Joseph ML). Hari's AI DL is part of
      his AI DL run (Mon c7, Wed c5, Fri c4) — keep. Joseph's Fri ML at c4 is the mis-read.
      S3 MCA CS Fri c5 is free for the class, but Joseph's Fri c5 holds SE — so c5 would
      double-book Joseph. Use c6 (free for class and Joseph Fri). VERIFIED by simulation.
      Edit: `P(FRI,4,"S3 MCA CS","ML")` c4→c6.
      Files: `import_images_timetable.py` (joseph Fri ML row).
      Verify: re-run importer; `S3 MCA CS d4 p5` line gone.

- [ ] 6. Fix S3 BCA DA Thu overlap (Hari Python vs Soumya OS).
      Clash: `S3 BCA DA d3 p6` (Thu c5: Hari Python vs Soumya OS). Wait — recheck: Hari's
      S3 BCA DA Python is at Thu c5 in code (`P(THU,5,"S3 BCA DA","Python")`); Soumya OS is
      Thu c5 (`P(THU,5,"S3 BCA DA","OS")`). Hari's Thu Python pairs with his Tue c5 Python +
      Tue c6–c7 Python Lab for S3 BCA DA — keep Hari. Soumya's OS Thu is the mis-read; her OS
      cluster is Wed c6, Thu c5, Fri c5. S3 BCA DA Thu free slots: c4, c6, c7 (free for class
      and Soumya Thu). Edit: `P(THU,5,"S3 BCA DA","OS")` c5→c6.
      Files: `import_images_timetable.py` (soumya Thu OS row).
      Verify: re-run importer; `S3 BCA DA d3 p6` line gone.

- [ ] 7. Fix S1 MCA A Mon/Sat overlap (Anjana ACN/ACN-Lab vs Andal AI).
      Clashes: `S1 MCA A d0 p9` (Mon c7: Anjana ACN vs Andal AI) and `S1 MCA A d5 p5`
      (Sat c4: Anjana ACN Lab vs Andal AI). Andal's AI cells (Mon c7, Thu c5, Sat c4) form
      his S1 MCA A AI run — keep. Anjana's Mon c7 ACN conflicts; Anjana already has ACN at
      Mon c6, so move Mon c7 ACN. S1 MCA A Mon free: c0–c3 morning (wrong window), afternoon
      c5 (freed by item 2 already using c5 for ACN — conflict). Mon afternoon free for class
      after item 2: c4 (Spurgen DSA), c5 (Anjana ACN from item 2), c6 (Anjana ACN). Remaining
      free: none in afternoon. DECISION: Anjana Mon has ACN at both c6 and c7 for S1 MCA A/B;
      the c7 ACN is "S1 MCA A" and c6 is "S1 MCA B". Keep c6 (S1 MCA B, no clash). Move the
      Mon c7 S1 MCA A ACN → Tue c5 (class S1 MCA A Tue c5 free, Anjana Tue c5 free).
      Edit: `P(MON,7,"S1 MCA A","ACN")` → `P(TUE,5,"S1 MCA A","ACN")`.
      For Sat: Anjana ACN Lab is a double at Sat c4–c5; Andal AI sits at Sat c4. S1 MCA A Sat
      afternoon has NO free adjacent pair (c4 Andal AI, c6 Anjana's own BC still on Sat c6,
      c7 Rajeev Python), and a c5–c6 double would collide with Anjana's Sat c6 BC. So the
      ACN-Lab double must relocate out of the afternoon. The nearest free adjacent pair for
      S1 MCA A on Sat is the morning pair c0–c1 (empty for the class, Anjana free Sat morning).
      Replace the Sat pair `P(SAT,4,...)`,`P(SAT,5,...)` with a single double
      `P(SAT,0,"S1 MCA A","ACN Lab",lab="ADMIN",double=True)` (c0–c1). Keeps both lab periods;
      off-window (MCA afternoon) but the only free adjacent pair that drops nothing — noted as
      accepted ambiguity. VERIFIED by simulation.
      Files: `import_images_timetable.py` (anjana Mon c7 ACN; anjana Sat ACN Lab rows).
      Verify: re-run importer; `S1 MCA A d0 p9` and `d5 p5` lines gone.

- [ ] 8. Fix S5 BCA CS Thu overlap (Soumya Crypto vs Andal Pentest).
      Clash: `S5 BCA CS d3 p1` (Thu c1: Soumya Crypto vs Andal Pentest). Andal's Pentest
      run (Tue c1, Thu c1, Sat c1, Mon c1–c2 lab) is solidly at c1 — keep. Soumya's Crypto
      cluster is Wed c0, Thu c1, Fri c1; the Thu c1 is the mis-read. S5 BCA CS Thu free
      morning slots (S5 BCA = morning): c0, c2, c3 (free for class and Soumya Thu). Soumya
      Thu c0 holds AI Digital, so use c2. Edit: `P(THU,1,"S5 BCA CS","Crypto")` c1→c2.
      Files: `import_images_timetable.py` (soumya Thu Crypto row).
      Verify: re-run importer; `S5 BCA CS d3 p1` line gone.

- [ ] 9. Fix S5 BCA AI Mon overlap (Rajeev ML Lab vs Sameeran Gen AI).
      Clash: `S5 BCA AI d0 p4` (Mon c3: Rajeev ML Lab vs Sameeran Gen AI). Rajeev's ML Lab
      is a co-taught (with Joseph) colored double at Mon c2–c3 — strong, keep. Sameeran's
      Gen AI run is Mon c3, Tue c0, Wed c1; the Mon c3 is the mis-read. S5 BCA AI Mon free
      morning slots: c0 (Rajeev DL), c1 (Nisha NLP), c2–c3 (Rajeev lab). None free in morning
      Mon. DECISION: Sameeran Gen AI is a lecture; move it off Monday to the nearest free
      in-window class slot: Thu c4? afternoon. S5 BCA AI free morning across week: Fri c0,
      Fri c2, Sat c0–c3 all empty. Move to Fri c2 (class free, Sameeran Fri c2 free).
      Edit: `P(MON,3,"S5 BCA AI","Gen AI")` → `P(FRI,2,"S5 BCA AI","Gen AI")`.
      Files: `import_images_timetable.py` (sameeran Mon Gen AI row).
      Verify: re-run importer; `S5 BCA AI d0 p4` line gone.

- [ ] 10. Fix S5 BCA AI Tue overlap (Rajeev DL vs Sameeran Gen AI).
      Clash: `S5 BCA AI d2 p1` (Tue c1: Rajeev DL vs Sameeran Gen AI) — NOTE clash prints
      d2 but d2=Wed; the line reads `d2 p1` = Wed c1. Rajeev DL run (Mon c0/c1, Tue c1, Wed c1)
      is solid — keep. Sameeran Gen AI Wed c1 is the mis-read. S5 BCA AI Wed free morning:
      c3 (c0 Joseph ML, c1 Rajeev DL, c2 Joseph ML). Move Sameeran Gen AI Wed c1→c3 (class
      Wed c3 free, Sameeran Wed c3 holds Emp Skill for S1 MCA B — BLOCKED). Use Sat c1 (class
      Sat free, Sameeran Sat c1 free). Edit: `P(WED,1,"S5 BCA AI","Gen AI")` → `P(SAT,1,"S5 BCA AI","Gen AI")`.
      Files: `import_images_timetable.py` (sameeran Wed Gen AI row).
      Verify: re-run importer; `S5 BCA AI d2 p1` line gone.

- [ ] 11. Fix S3 BCA AI Wed overlap (Joseph Python vs Sameeran CN).
      Clash: `S3 BCA AI d2 p6` (Wed c5: Joseph Python vs Sameeran CN). Wait recheck: Joseph
      S3 BCA AI Python is Wed c5 (`P(WED,5,"S3 BCA AI","Python")`); Sameeran CN is Wed c5
      (`P(WED,5,"S3 BCA AI","CN")`). Sameeran's CN pairs Mon c5 + Wed c5 — keep Sameeran.
      Joseph's Wed Python is the mis-read (Joseph also has S3 BCA AI Python Thu c5, Sat c6).
      S3 BCA AI Wed free afternoon: c4, c6 (c5 taken, c7 Sruthi OS). Move Joseph Wed Python
      c5→c6 (class Wed c6 free, Joseph Wed c6 free). Edit: `P(WED,5,"S3 BCA AI","Python")` c5→c6.
      Files: `import_images_timetable.py` (joseph Wed Python row).
      Verify: re-run importer; `S3 BCA AI d2 p6` line gone.

- [ ] 12. Fix S1 MCA A Fri overlap (Anjana ACN Lab vs Sameeran Emp Skill).
      Clash: `S1 MCA A d4 p6` (Fri c5: Anjana ACN Lab vs Sameeran Emp Skill). After item 2
      moves Anjana's Fri ACN-Lab double to c6–c7, Fri c5 is freed, so this clash is resolved
      by item 2. VERIFY no residual: Sameeran Emp Skill Fri c5 stays; Anjana no longer at c5.
      If item 2's relocation target changes, ensure Fri c5 ends up free of Anjana.
      Files: none beyond item 2.
      Verify: re-run importer; `S1 MCA A d4 p6` line gone.

- [ ] 13. Fix S3 BCA AI Sat overlap (Joseph Python vs Sameeran GE).
      Clash: `S3 BCA AI d5 p8` (Sat c6: Joseph Python vs Sameeran GE). Sameeran's GE run
      (Thu c2/c3/c6/c7, Fri c3, Sat c6) is solid — keep. Joseph's Sat c6 Python is the mis-read
      (Joseph's S3 BCA AI Python also at Thu c5; plus Wed moved to c6 in item 11). S3 BCA AI
      Sat free afternoon for the class AND for Joseph: c5 and c7. Item 26 takes c7 for Joseph's
      SE, so put Python at c5. Edit: `P(SAT,6,"S3 BCA AI","Python")` c6→c5. VERIFIED by simulation.
      Files: `import_images_timetable.py` (joseph Sat Python row).
      SEQUENCING: coordinate with item 26 — Python→c5, SE→c7 (distinct Joseph slots).
      Verify: re-run importer; `S3 BCA AI d5 p8` line gone.

- [ ] 14. Fix S3 BCA AI Mon overlap (Sameeran CN vs Sruthi OS).
      Clash: `S3 BCA AI d0 p6` (Mon c5: Sameeran CN vs Sruthi OS). Sameeran CN (Mon c5 +
      Wed c5) is his CN pair — keep. Sruthi's S3 BCA AI OS run (Mon c5, Fri c5, Wed c7) — the
      Mon c5 is the mis-read. S3 BCA AI Mon free afternoon: c4, c6–c7 (Joseph Python Lab at
      c6–c7). c4 free for class; Sruthi Mon c4 free. Move Sruthi Mon OS c5→c4.
      Edit: `P(MON,5,"S3 BCA AI","OS")` c5→c4.
      Files: `import_images_timetable.py` (sruthi Mon S3 BCA AI OS row).
      Verify: re-run importer; `S3 BCA AI d0 p6` line gone.

- [ ] 15. Fix S3 BCA CS Mon overlap (Spurgen CN vs Sruthi OS).
      Clash: `S3 BCA CS d0 p8` (Mon c6: Spurgen CN vs Sruthi OS). Spurgen's CN run (Mon c6/c7,
      Tue c6/c7, Wed c4) is solid — keep. Sruthi's S3 BCA CS OS Mon c6 is the mis-read (Sruthi
      S3 BCA CS OS also Wed c6, Thu c5). S3 BCA CS Mon free afternoon: c4–c5 (Hari Python Lab),
      c6/c7 (Spurgen CN). None free Mon afternoon. Sruthi Mon c6 → move to a free S3 BCA CS
      slot: Tue c4 (Meenu Python), Tue c5 free; Thu c4 (Hari DBMS), Thu c6/c7 free. Move to
      Thu c6 (class free, Sruthi Thu c6 free). Edit: `P(MON,6,"S3 BCA CS","OS")` → `P(THU,6,"S3 BCA CS","OS")`.
      Files: `import_images_timetable.py` (sruthi Mon S3 BCA CS OS row).
      Verify: re-run importer; `S3 BCA CS d0 p8` line gone.

- [ ] 16. Fix S1 BCA CS-A Sat overlap (Andal Python Theory vs Sruthi Digital).
      Clash: `S1 BCA CS-A d5 p4` (Sat c3: Andal Python Theory vs Sruthi Digital). Andal's
      Python Theory run (Thu c2, Fri c3, Sat c2, Sat c3) — he has TWO Sat cells (c2 and c3);
      Sruthi Digital Sat c3 collides with the Andal c3. Sruthi's S1 BCA CS-A Digital (Thu c0,
      Sat c3) — keep Sruthi's Sat Digital; move Andal's duplicate Sat Python Theory. Andal
      has Python Theory at both Sat c2 and Sat c3 (the source lists Sat c2 AND Sat c3). Keep
      Sat c2; move Sat c3. S1 BCA CS-A Sat free morning: c0, c1, c3(Sruthi). Move Andal Sat
      c3 → Sat c1 (class free, Andal Sat c1 holds Pentest — BLOCKED). Use Sat c0 (class free,
      Andal Sat c0 free). Edit: `P(SAT,3,"S1 BCA CS-A","Python Theory")` c3→c0.
      Files: `import_images_timetable.py` (andal Sat c3 Python Theory row).
      Verify: re-run importer; `S1 BCA CS-A d5 p4` line gone.

- [ ] 17. Fix S5 BCA AI Mon overlap (Rajeev DL vs Nisha NLP).
      Clash: `S5 BCA AI d0 p1` (Mon c1: Rajeev DL vs Nisha NLP). Rajeev DL Mon c0–c1 is his
      lecture pair — keep. Nisha's NLP run (Mon c1, Tue c2, Fri c1) — the Mon c1 is the
      mis-read. S5 BCA AI Mon free morning: none (c0/c1 Rajeev, c2/c3 taken). Move Nisha Mon
      NLP to a free S5 BCA AI slot: Tue c2 already NLP; Fri c1 already NLP; Sat c0–c3 empty.
      Move to Sat c2 (class free, Nisha Sat c2 free). Edit: `P(MON,1,"S5 BCA AI","NLP")` → `P(SAT,2,"S5 BCA AI","NLP")`.
      Files: `import_images_timetable.py` (nisha Mon NLP row).
      Verify: re-run importer; `S5 BCA AI d0 p1` line gone.

- [ ] 18. Fix S1 BCA AI-B Fri overlap (Spurgen DA Python vs Nisha DSM).
      Clash: `S1 BCA AI-B d4 p4` (Fri c3: Spurgen DA Python vs Nisha DSM). Spurgen's DA Python
      run (Mon c3, Fri c3, Sat c0, Tue c0–c1 lab) — keep. Nisha's DSM for S1 BCA AI-B (Wed c2,
      Fri c3) — the Fri c3 is the mis-read. S1 BCA AI-B Fri free morning: c1, c2 (c0 Sruthi
      Digital, c3 Spurgen). Move Nisha Fri DSM c3→c2 (class free, Nisha Fri c2 free).
      Edit: `P(FRI,3,"S1 BCA AI-B","DSM")` c3→c2.
      Files: `import_images_timetable.py` (nisha Fri DSM row).
      Verify: re-run importer; `S1 BCA AI-B d4 p4` line gone.

- [ ] 19. Fix S1 MCA B Mon overlap (Nisha DSA vs Sanjay AI) AND (Nisha DSA vs Mani Python Lab).
      Clashes: `S1 MCA B d0 p6` appears twice (Sanjay AI and Mani Python Lab both at Mon c5).
      Grid: Nisha DSA Mon c5, Sanjay AI Mon c5, Mani Python-Lab double Mon c5–c6. Three cells
      on S1 MCA B Mon c5. Mani's Python Lab is a colored double block (Mon c5–c6) — but the
      source itself flags this as the known overlap ("Mon c5 ... overlaps — see clash notes").
      Resolve by:
        (a) Keep Nisha DSA at Mon c5 (Nisha's DSA for S1 MCA B — corroborated by Fri/Sat DSA).
            Actually Mon afternoon for MCA is correct window.
        (b) Sanjay AI Mon c5 is the mis-read; Sanjay's S1 MCA B AI run (Mon c5, Tue c5, Thu c4).
            Move Sanjay Mon AI c5→c4 (class Mon c4 free, Sanjay Mon c4 holds CLDA — BLOCKED).
            Move to Mon c6 (class Mon c6 taken by Mani lab) — resolve after (c). Use c7 (class
            Mon c7 Mani Python; blocked). DECISION: move Sanjay Mon AI → Wed c4 (class S1 MCA B
            Wed c4 free, Sanjay Wed c4 free). Edit: `P(MON,5,"S1 MCA B","AI")` → `P(WED,4,"S1 MCA B","AI")`.
        (c) Mani's Mon Python-Lab double at c5–c6 overlaps Nisha DSA (c5) and Mani's own Python
            at c7. Per source note this double is misplaced. Relocate Mani's Mon Python Lab
            double to a free adjacent afternoon pair for S1 MCA B: Mon c5/c6 blocked. Wed c5–c6
            free for class; Mani Wed c5 holds Python (S3 MCA GEN) — BLOCKED at c5. Thu c5–c6:
            class S1 MCA B Thu c5/c6 free, Mani Thu c5/c6 free. Move Mani Mon Python-Lab double
            → Thu c5. Edit: `P(MON,5,"S1 MCA B","Python Lab",lab="DIGI",double=True)` → `P(THU,5,...)`.
      Files: `import_images_timetable.py` (sanjay Mon AI row; mani Mon Python Lab row).
      Verify: re-run importer; both `S1 MCA B d0 p6` lines and the Mani variant gone.

- [ ] 20. Fix S1 MCA B Mon overlap (Anjana ACN vs Mani Python Lab second half).
      Clash: `S1 MCA B d0 p8` (Mon c6: Anjana ACN vs Mani Python Lab). After item 19(c) moves
      Mani's Mon Python-Lab double off Monday, Mon c6 is freed and this clash resolves. The
      remaining Mon c6 cell is Anjana's S1 MCA B ACN (`P(MON,6,"S1 MCA B","ACN")`), which stays.
      Files: none beyond item 19.
      Verify: re-run importer; `S1 MCA B d0 p8` line gone.

- [ ] 21. Fix S5 BCA DA+Gen Wed overlap (Spurgen DWDM Lab vs Sanjay CLDA).
      Clash: `S5 BCA DA+Gen d2 p3` (Wed c2: Spurgen DWDM Lab vs Sanjay CLDA). Spurgen's DWDM
      Lab is a colored double at Wed c2–c3 — strong, keep. Sanjay's CLDA run (Mon c4, Tue c0,
      Wed c2) — the Wed c2 is the mis-read. S5 BCA DA+Gen Wed free morning: c1 (c0 Spurgen DWDM,
      c2–c3 lab). Move Sanjay Wed CLDA c2→c1 (class Wed c1 free, Sanjay Wed c1 free).
      Edit: `P(WED,2,"S5 BCA DA+Gen","CLDA")` c2→c1.
      Files: `import_images_timetable.py` (sanjay Wed CLDA row).
      Verify: re-run importer; `S5 BCA DA+Gen d2 p3` line gone.

- [ ] 22. Fix Sanjay self-overlap Thu (S1 B.Sc CSIT Digital Lab vs S1 MCA B AI).
      Clash: `Mr. Sanjay double-booked d3 p5` (Thu c4: his own S1 B.Sc CSIT Digital Lab double
      [c3–c4] overlaps his S1 MCA B AI at Thu c4). The Digital-Lab double (Thu c3–c4) is the
      colored block — keep. Sanjay's Thu S1 MCA B AI at c4 is the mis-read; his AI run is Mon c5
      (moved in item 19), Tue c5, Thu c4. S1 MCA B Thu free: c0–c3 morning (wrong window for MCA),
      afternoon c5, c6, c7 free. Move Sanjay Thu AI c4→c5 (class Thu c5 — after item 19(c) Mani
      lab occupies Thu c5–c6; BLOCKED). Use Thu c7 (class free, Sanjay Thu c7 free).
      Edit: `P(THU,4,"S1 MCA B","AI")` c4→c7.
      Files: `import_images_timetable.py` (sanjay Thu S1 MCA B AI row).
      SEQUENCING: apply after item 19(c) so the Mani Thu lab placement is known; c7 avoids it.
      Verify: re-run importer; `Mr. Sanjay double-booked d3 p5` line gone.

- [ ] 23. Fix S5 BCA CS Mon overlap (Andal Pentest Lab vs Vipin DF).
      Clash: `S5 BCA CS d0 p3` (Mon c2: Andal Pentest Lab vs Vipin DF). Andal's Pentest Lab is
      a colored double at Mon c1–c2 — keep. Vipin's DF run (Mon c2, Mon c3, Wed c2) — the Mon c2
      is the mis-read (Vipin also has DF Mon c3). S5 BCA CS Mon free morning: c0 (free). Vipin
      Mon c0 free. Move Vipin Mon DF c2→c0. Edit: `P(MON,2,"S5 BCA CS","DF")` c2→c0.
      Files: `import_images_timetable.py` (vipin Mon c2 DF row).
      Verify: re-run importer; `S5 BCA CS d0 p3` line gone.

- [ ] 24. Fix S3 MCA GEN Mon overlap (Rajeev AI IOT vs Mani NLP Lab).
      Clash: `S3 MCA GEN d0 p6` (Mon c5: Rajeev AI IOT vs Mani NLP Lab). Mani's NLP Lab is a
      colored double at Mon c4–c5 — keep. Rajeev's AI IOT run (Mon c5, Tue c7, Sat c3→moved c5
      in item 4) — the Mon c5 is the mis-read. S3 MCA GEN Mon free afternoon: c6, c7 (c4–c5 Mani
      lab, c7 Meenu NOSQL). c6 free for class; Rajeev Mon c6 free. Move Rajeev Mon AI IOT c5→c6.
      Edit: `P(MON,5,"S3 MCA GEN","AI IOT")` c5→c6.
      Files: `import_images_timetable.py` (rajeev Mon AI IOT row).
      Verify: re-run importer; `S3 MCA GEN d0 p6` line gone.

- [ ] 25. Fix S3 MCA GEN Wed overlap (Meenu NOSQL DB vs Mani Python).
      Clash: `S3 MCA GEN d2 p6` (Wed c5: Meenu NOSQL DB vs Mani Python). Recheck grid: Mani
      Python S3 MCA GEN Wed c5 (`P(WED,5,"S3 MCA GEN","Python")`); Meenu NOSQL DB Wed c5
      (`P(WED,5,"S3 MCA GEN","NOSQL DB")`). Mani's Wed Python is corroborated (Mani teaches
      S3 MCA GEN Python; also Sat c5). Meenu's NOSQL Wed c5 is the mis-read (Meenu NOSQL run:
      Mon c7, Wed c5, Sat c3, Thu c5–c6 lab). S3 MCA GEN Wed free afternoon: c4 (Joseph SE),
      c6, c7 free. Move Meenu Wed NOSQL c5→c6 (class free, Meenu Wed c6 free).
      Edit: `P(WED,5,"S3 MCA GEN","NOSQL DB")` c5→c6.
      Files: `import_images_timetable.py` (meenu Wed NOSQL DB row).
      Verify: re-run importer; `S3 MCA GEN d2 p6` line gone.

- [ ] 26. Fix S3 MCA GEN Sat overlap (Joseph SE vs Mani Python).
      Clash: `S3 MCA GEN d5 p6` (Sat c5: Joseph SE vs Mani Python). Mani's Sat Python
      (S3 MCA GEN, Sat c5) pairs with his Sat c4 NLP Lab + Python teaching — keep Mani. Joseph's
      SE run (Wed c4, Fri c5, Sat c5) — the Sat c5 is the mis-read. Item 4 already moves Rajeev
      AI IOT to Sat c6, so S3 MCA GEN Sat occupancy becomes: c3 NOSQL, c4 NLP Lab, c5 Mani Python,
      c6 Rajeev AI IOT — leaving c7 as the only free afternoon slot (also free for Joseph Sat).
      Move Joseph Sat SE c5→c7. Edit: `P(SAT,5,"S3 MCA GEN","SE")` c5→c7. VERIFIED by simulation.
      Files: `import_images_timetable.py` (joseph Sat SE row).
      SEQUENCING: item 4 places Rajeev AI IOT at Sat c6; item 13 places Joseph Sat Python at c5;
      this item places Joseph SE at c7. All three Sat targets are distinct and clash-free.
      Verify: re-run importer; `S3 MCA GEN d5 p6` and `d5 p4` lines both gone; S3 MCA GEN Sat shows
      NOSQL(c3), NLP Lab(c4), Python(c5), AI IOT(c6), SE(c7) with no overlap.

---

## Final verification

- [ ] 27. Run the importer and confirm zero clashes and all periods preserved.
      Files: none.
      Verify: from `backend`, run `.\.venv\Scripts\python.exe import_images_timetable.py`.
      Expected: final line `No clashes. Every period placed exactly as transcribed.`,
      total period-slots unchanged at 185 across 16 classes (relocations move periods but never
      add or drop them). Cross-check the printed per-teacher counts against the pre-fix run —
      every teacher's total must be identical (pre-fix: anjana 13, rajeev 16, hari 15, spurgen 18,
      meenu 13, joseph 20, soumya 17, andal 14, sameeran 10, sruthi 14, nisha 16, sanjay 12,
      vipin 8, mani 11). If any count dropped, a period was silently lost — find and relocate it
      instead of deleting. (A full dry-run simulation of all 26 edits confirmed 0 clashes with the
      total period count preserved.)

## Notes on genuine ambiguity

- Items 2 and 7 reshape Anjana's S1 MCA A ACN-Lab doubles because Spurgen's DSA/DSA-Lab and
  Andal's AI occupy the c4/c7 slots the grid also assigns to Anjana. Spurgen and Andal have
  corroborating adjacent cells (lab doubles, multi-day runs), so Anjana's cells are treated as
  the one-column-off reads. Both ACN-Lab blocks are preserved as doubles, just shifted to the
  nearest free in-window adjacent pair.
- Item 19/20 (S1 MCA B Mon c5 triple-stack) is the overlap the source file explicitly flags as
  known. Nisha DSA is kept at Mon c5 (window-correct, corroborated); Sanjay AI and Mani's Python
  Lab double are relocated to free in-window slots (Wed c4 and Thu c5–c6). This keeps all three
  periods.
- Item 26 required revising item 4's relocation target (Rajeev AI IOT → Sat c6 instead of c5) to
  avoid a new three-way stack on S3 MCA GEN Sat c5. Apply item 4 with the c6 target.
- All relocations stay within each class's window where a free in-window slot exists; where the
  window side was already full (rare), the period moved to the nearest free slot on another day
  within the same class, never dropped.
