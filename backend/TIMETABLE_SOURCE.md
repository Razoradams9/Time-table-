# Timetable source transcription (from the 14 teacher grid images)

This is the authoritative transcription of the department's 14 per-teacher
timetable images, used by `import_images_timetable.py`. The orchestrator
transcribed these directly from the images the user supplied. Use this as the
ground truth when resolving import clashes — but note that some cells may have
been slightly mis-read (wrong time column), so a clash is a signal to re-check
the intended placement.

## Grid structure

- Columns (time): `8:30-9:25 | 9:25-10:20 | BREAK 10:20-10:40 | 10:40-11:35 |
  11:35-12:30 | 12:30-1:25 | 1:25-2:20 | BREAK 2:20-2:40 | 2:40-3:35 | 3:35-4:30`
- So there are **8 teaching columns**, ordinal 0..7:
  - col 0 = 08:30, col 1 = 09:25, col 2 = 10:40, col 3 = 11:35,
    col 4 = 12:30, col 5 = 13:25, col 6 = 14:40, col 7 = 15:35
- Rows: Mon, Tue, Wed, Thu, Fri, Sat (day 0..5).
- In the backend, `TimeSlot.period_index` uses the values `[0,1,3,4,5,6,8,9]`
  for columns 0..7 (gaps mark the two breaks). The importer maps column ordinal
  -> period_index via `COL_TO_PIDX = [0,1,3,4,5,6,8,9]`.
- Green/orange/colored cells that span two columns are **lab double blocks**
  (`double=True`), occupying the column + the next column. A colored cell in the
  last column (col 7) is a single-period lab (cannot extend past the day).
- Labs name a room: "Admin Lab" (ADMIN), "Digi Lab" (DIGI), "Digital Lab"
  (DIGITAL). Lectures get an auto-assigned lecture room.
- Co-taught labs name two teachers (e.g. "Meenu & Hari", "Joseph & Soumya",
  "Rajeev & Joseph"). Each such lab is listed ONCE on the primary teacher with
  `co=<other>`; the co-teacher is wired in automatically and must NOT be listed
  again on the co-teacher's row.

## Window policy (hard constraint in the generator, informational here)

- S1 & S5 BCA classes -> MORNING columns (0-3)
- S3 (any) and all MCA classes -> AFTERNOON columns (4-7)

The imported grids may not perfectly obey this (the images are the source of
truth), but it explains why some classes cluster in certain columns.

## Per-teacher transcription

Format: `Day colN: ClassName — Subject [lab=ROOM] [co=teacher] [double]`

### Anjana (HOD) — anjana@college.edu
- Mon c4: S1 MCA A — ACN
- Mon c6: S1 MCA B — ACN
- Mon c7: S1 MCA A — ACN
- Tue c4: S1 MCA B — ACN
- Wed c4: S3 MCA CS — BC
- Wed c6: S3 MCA CS — BC
- Wed c7: S3 MCA CS — BC Lab [lab=DIGI] (single, last slot, "4th hr")
- Thu c4: S1 MCA A — ACN Lab [lab=ADMIN]
- Fri c4,c5: S1 MCA A — ACN Lab [lab=ADMIN]
- Sat c4,c5: S1 MCA A — ACN Lab [lab=ADMIN]
- Sat c6: S3 MCA CS — BC

### Dr. Rajeev — rajeev@college.edu
- Mon c0: S5 BCA AI — DL
- Mon c1: S5 BCA AI — DL
- Mon c2,c3: S5 BCA AI — ML Lab [lab=ADMIN] [co=joseph] [double]
- Mon c5: S3 MCA GEN — AI IOT
- Tue c1: S5 BCA AI — DL
- Tue c6: S1 MCA A — Python
- Tue c7: S3 MCA GEN — AI IOT
- Wed c1: S5 BCA AI — DL
- Wed c3: S1 MCA A — Python
- Wed c4,c5: S1 MCA A — Python Lab [lab=DIGI] [double]
- Thu c0: S5 BCA AI — DL Lab [lab=ADMIN] [co=joseph] [double]
- Sat c3: S3 MCA GEN — AI IOT
- Sat c7: S1 MCA A — Python

### Dr. Hari Narayanan — hari@college.edu
- Mon c4,c5: S3 BCA CS — Python Lab [lab=ADMIN] [co=meenu] [double]
- Mon c7: S3 MCA CS — AI DL
- Tue c4: S3 BCA CS — DBMS
- Tue c5: S3 BCA DA — Python
- Tue c6,c7: S3 BCA DA — Python Lab [lab=ADMIN] [double]
- Wed c5: S3 MCA CS — AI DL
- Wed c6,c7: S3 MCA CS — DL Lab [lab=ADMIN] [double]
- Thu c4: S3 BCA CS — DBMS
- Thu c5: S3 BCA DA — Python
- Fri c4: S3 MCA CS — AI DL
- Fri c5,c6: S3 BCA CS — DBMS Lab [lab=ADMIN] [co=meenu] [double]
- Sat c4: S3 BCA CS — DBMS
- Sat c6: S3 BCA DA — Python

### Dr. Spurgen Ratheash — spurgen@college.edu
- Mon c0: S5 BCA DA+Gen — DWDM
- Mon c3: S1 BCA AI-B — DA Python
- Mon c4: S1 MCA A — DSA
- Mon c6: S3 BCA CS — CN
- Mon c7: S3 BCA CS — CN
- Tue c0,c1: S1 BCA AI-B — DA Python Lab [lab=ADMIN] [double]
- Tue c6: S3 BCA CS — CN
- Tue c7: S3 BCA CS — CN
- Wed c0: S5 BCA DA+Gen — DWDM
- Wed c2,c3: S5 BCA DA+Gen — DWDM Lab [lab=DIGI] [double]
- Wed c4: S3 BCA CS — CN
- Wed c6,c7: S1 MCA A — DSA Lab [lab=DIGI] [double]
- Thu c4: S1 MCA A — DSA
- Fri c1: S5 BCA DA+Gen — DWDM
- Fri c3: S1 BCA AI-B — DA Python
- Fri c4: S1 MCA A — DSA Lab
- Sat c0: S1 BCA AI-B — DA Python
- Sat c3: S1 MCA A — DSA

### Dr. Meenu Suresh — meenu@college.edu
- Mon c1: S5 BCA DA+Gen — R Prog
- Mon c2,c3: S5 BCA DA+Gen — R Prog Lab [lab=ADMIN] [double]
- Mon c4,c5: S3 BCA CS — (co-taught Python Lab with Hari — on Hari as primary)
- Mon c7: S3 MCA GEN — NOSQL DB
- Tue c4: S3 BCA CS — Python
- Wed c4: S3 BCA CS — Python
- Wed c5: S3 MCA GEN — NOSQL DB
- Thu c0: S5 BCA DA+Gen — R Prog
- Thu c5: S3 MCA GEN — NOSQL DB Lab [lab=DIGI] [double]
- Fri c5,c6: S3 BCA CS — (co-taught DBMS Lab with Hari — on Hari as primary)
- Sat c3: S3 MCA GEN — NOSQL DB
- Sat c6: S3 BCA CS — Python

### Mr. Joseph James — joseph@college.edu
- Mon c2,c3: S5 BCA AI — ML Lab (co-taught with Rajeev — on Rajeev as primary)
- Mon c5: S3 MCA CS — ML
- Mon c6,c7: S3 BCA AI — Python Lab [lab=ADMIN] [co=soumya] [double]
- Tue c4,c5: S3 BCA AI — DBMS Lab [lab=ADMIN] [co=soumya] [double]
- Tue c6: S3 MCA CS — ML Lab [lab=DIGITAL] [double]
- Wed c0: S5 BCA AI — ML
- Wed c2: S5 BCA AI — ML
- Wed c4: S3 MCA GEN — SE
- Wed c5: S3 BCA AI — Python
- Thu c0: S5 BCA AI — DL Lab (co-taught with Rajeev — on Rajeev as primary)
- Thu c5: S3 BCA AI — Python
- Fri c4: S3 MCA CS — ML
- Fri c5: S3 MCA GEN — SE
- Sat c4: S3 MCA CS — ML
- Sat c5: S3 MCA GEN — SE
- Sat c6: S3 BCA AI — Python

### Ms. Soumya K — soumya@college.edu
- Mon c0,c1: S1 BCA AI-A — AI Digital Lab [lab=ADMIN] [double] ("2nd hr")
- Mon c6,c7: S3 BCA AI — Python (co-taught with Joseph — on Joseph as primary)
- Tue c0: S1 BCA AI-A — AI Digital
- Tue c4,c5: S3 BCA AI — DBMS Lab (co-taught with Joseph — on Joseph as primary)
- Tue c6: S3 BCA AI — DBMS
- Wed c0: S5 BCA CS — Crypto
- Wed c6: S3 BCA DA — OS
- Thu c0: S1 BCA AI-A — AI Digital
- Thu c1: S5 BCA CS — Crypto
- Thu c5: S3 BCA DA — OS
- Fri c1: S5 BCA CS — Crypto
- Fri c4: S3 BCA AI — DBMS
- Fri c5: S3 BCA DA — OS
- Sat c0: S1 BCA AI-A — AI Digital
- Sat c4: S3 BCA AI — DBMS

### Dr. Andal V — andal@college.edu
- Mon c1,c2: S5 BCA CS — Pentest Lab [lab=DIGI] [double]
- Mon c3,c4: S1 BCA CS-A — Python Lab [lab=DIGITAL] [double]
- Mon c7: S1 MCA A — AI
- Tue c1: S5 BCA CS — Pentest
- Wed c0: S1 BCA CS-B — Python Lab [lab=DIGI] [double]
- Thu c1: S5 BCA CS — Pentest
- Thu c2: S1 BCA CS-A — Python Theory
- Thu c5: S1 MCA A — AI
- Fri c3: S1 BCA CS-A — Python Theory
- Fri c4: S1 BCA CS-B — Python Theory
- Sat c1: S5 BCA CS — Pentest
- Sat c2: S1 BCA CS-A — Python Theory
- Sat c3: S1 BCA CS-A — Python Theory
- Sat c4: S1 MCA A — AI
- (note: image also shows "TDPCL" at Fri c6 — ignored/no class)

### Mr. Sameeran — sameeran@college.edu
- Mon c3: S5 BCA AI — Gen AI
- Mon c5: S3 BCA AI — CN
- Tue c0: S5 BCA AI — Gen AI
- Tue c3: S1 MCA A — Emp Skill
- Wed c1: S5 BCA AI — Gen AI
- Wed c3: S1 MCA B — Emp Skill
- Wed c5: S3 BCA AI — CN
- Thu c1: S1 B.Sc IT — AI Literacy
- Thu c2: S5 BCA AI — GE
- Thu c3: S5 BCA AI — GE
- Thu c6: S3 BCA AI — GE
- Thu c7: S3 BCA AI — GE
- Fri c3: S5 BCA AI — GE
- Fri c5: S1 MCA A — Emp Skill
- Sat c6: S3 BCA AI — GE

### Dr. Sruthi — sruthi@college.edu
- Mon c0,c1: S1 BCA AI-B — Digital Lab [lab=ADMIN] [double] ("1st hr")
- Mon c2: S3 BCA CS — DSM
- Mon c5: S3 BCA AI — OS
- Mon c6: S3 BCA CS — OS
- Tue c0,c1: S1 BCA CS-A — Digital Lab [lab=DIGI] [double] ("1st hr")
- Wed c3: S1 BCA AI-B — Digital
- Wed c6: S3 BCA CS — OS
- Wed c7: S3 BCA AI — OS
- Thu c0: S1 BCA CS-A — Digital
- Thu c5: S3 BCA CS — OS
- Fri c0: S1 BCA AI-B — Digital
- Fri c2: S1 BCA CS-B — DSM
- Fri c5: S3 BCA AI — OS
- Sat c3: S1 BCA CS-A — Digital
- Sat c4: S1 BCA AI-B — Digital

### Dr. Nisha — nisha@college.edu
- Mon c1: S5 BCA AI — NLP
- Mon c4: S3 BCA DA — DBMS
- Mon c5: S1 MCA B — DSA
- Tue c2: S5 BCA AI — NLP
- Tue c4: S3 BCA DA — DBMS
- Wed c2: S1 BCA AI-B — DSM
- Wed c4,c5: S3 BCA DA — DBMS Lab [lab=ADMIN] [double]
- Thu c1: S1 BCA AI-A — DSM
- Fri c1: S5 BCA AI — NLP
- Fri c3: S1 BCA AI-B — DSM
- Fri c4: S1 MCA B — DSA
- Fri c5,c6: S1 MCA B — DSA Lab [lab=ADMIN] [double] ("2nd hr")
- Sat c3,c4: S1 MCA B — DSA Lab [lab=ADMIN] [double] ("2nd hr")
- Sat c5: S3 BCA DA — DBMS
- Sat c7: S1 MCA B — DSA

### Mr. Sanjay — sanjay@college.edu
- Mon c0: S1 B.Sc CSIT — Digital
- Mon c1: S1 BCA CS-B — Digital
- Mon c4: S5 BCA DA+Gen — CLDA
- Mon c5: S1 MCA B — AI
- Tue c0: S5 BCA DA+Gen — CLDA
- Tue c1: S1 BCA CS-B — Digital
- Tue c5: S1 MCA B — AI
- Wed c2: S5 BCA DA+Gen — CLDA
- Thu c0: S1 BCA CS-B — Digital Lab
- Thu c3,c4: S1 B.Sc CSIT — Digital Lab [lab=ADMIN] [double]
- Thu c4: S1 MCA B — AI
- Fri c0: S1 B.Sc CSIT — Digital
- Sat c0: S1 BCA CS-B — Digital
- Sat c2: S1 B.Sc CSIT — Digital

### Mr. Vipin — vipin@college.edu
- Mon c2: S5 BCA CS — DF
- Mon c3: S5 BCA CS — DF
- Mon c4: S5 BCA CS — CF
- Mon c7: S5 BCA CS — Cyber Lab [lab=DIGITAL] (single, last slot)
- Tue c2,c3: S5 BCA CS — Digital Forensics Lab [lab=DIGI] [double]
- Tue c5: S5 BCA CS — CF
- Wed c2: S5 BCA CS — DF
- Sat c5: S5 BCA CS — CF

### Dr. Manivasagam — mani@college.edu
- Mon c4,c5: S3 MCA GEN — NLP Lab [lab=DIGI] [double]
- Mon c5: S1 MCA B — Python Lab [lab=DIGI] [double]  (overlaps — see clash notes)
- Mon c7: S1 MCA B — Python
- Tue c1: S1 MCA B — PFUC
- Tue c5: S3 MCA GEN — NLP
- Tue c6: S3 MCA GEN — NLP
- Wed c5: S3 MCA GEN — Python
- Thu c1: S1 MCA B — PFUC
- Thu c3,c4: S3 MCA GEN — Python Lab [lab=DIGI] [double]
- Fri c3: S3 MCA GEN — C Lab [lab=ADMIN]
- Fri c4: S3 MCA GEN — NLP Lab [lab=DIGI]
- Sat c1: S1 MCA B — PFUC
- Sat c4: S3 MCA GEN — NLP Lab [lab=DIGI]
- Sat c5: S3 MCA GEN — Python

## Known remaining clashes to resolve (as of last import run)

These are cross-teacher conflicts where two grids place the same class in the
same slot, or a column was likely mis-read. Re-check each against the image
descriptions above and adjust the period/column (and lab span) so each class
sits in exactly one place per slot, honoring the window policy where possible.
Do NOT silently drop a period — relocate it to the teacher's / class's intended
slot. A clash usually means one of the two cells was transcribed one column off.

(See the importer output for the current list; expect ~32 to start.)
