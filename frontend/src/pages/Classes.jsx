import { useState } from "react";
import { useNavigate } from "react-router-dom";

/* ── Icon helper ── */
const Ic = ({ d, size = 16 }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
    width={size} height={size} style={{ display:"inline-block", verticalAlign:"middle", flexShrink:0 }}>
    {d}
  </svg>
);
const IcUsers    = (p) => <Ic {...p} d={<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></>} />;
const IcGrad     = (p) => <Ic {...p} d={<><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></>} />;
const IcBook     = (p) => <Ic {...p} d={<><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>} />;
const IcEye      = (p) => <Ic {...p} d={<><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>} />;
const IcEdit     = (p) => <Ic {...p} d={<><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></>} />;
const IcMore     = (p) => <Ic {...p} d={<><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></>} />;
const IcSearch   = (p) => <Ic {...p} d={<><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></>} />;
const IcX        = (p) => <Ic {...p} d={<><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>} />;
const IcPlus     = (p) => <Ic {...p} d={<><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>} />;
const IcCalendar = (p) => <Ic {...p} d={<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>} />;
const IcChevron  = (p) => <Ic {...p} d={<><polyline points="6 9 12 15 18 9"/></>} />;
const IcChevRight= (p) => <Ic {...p} d={<><polyline points="9 18 15 12 9 6"/></>} />;
const IcTimetable= (p) => <Ic {...p} d={<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>} />;

/* ── Central class data (shared with Substitutions / Timetable) ──
   BCA-only, using the real department faculty. */
export const CLASS_DATA = [
  { id:1,  name:"S1 BCA AI-A", program:"BCA", spec:"Artificial Intelligence", sem:1, students:60, status:"Active",
    subjects:["Python Programming","Discrete Structures & Maths","Digital Fundamentals","Artificial Intelligence"],
    teachers:[{name:"Dr. Rajeev",subject:"Python Programming"},{name:"Dr. Nisha",subject:"Discrete Structures & Maths"},{name:"Ms. Soumya K",subject:"Digital Fundamentals"},{name:"Mrs. Anjana Chandran",subject:"Artificial Intelligence"}] },
  { id:2,  name:"S1 BCA AI-B", program:"BCA", spec:"Artificial Intelligence", sem:1, students:58, status:"Active",
    subjects:["Python Programming","Discrete Structures & Maths","Digital Fundamentals"],
    teachers:[{name:"Dr. Spurgen Ratheash",subject:"Python Programming"},{name:"Dr. Nisha",subject:"Discrete Structures & Maths"},{name:"Dr. Sruthi",subject:"Digital Fundamentals"}] },
  { id:3,  name:"S1 BCA CS-A", program:"BCA", spec:"Cyber Security", sem:1, students:59, status:"Active",
    subjects:["Python Programming","Digital Fundamentals","Discrete Structures & Maths"],
    teachers:[{name:"Dr. Andal V",subject:"Python Programming"},{name:"Dr. Sruthi",subject:"Digital Fundamentals"},{name:"Dr. Sruthi",subject:"Discrete Structures & Maths"}] },
  { id:4,  name:"S1 BCA CS-B", program:"BCA", spec:"Cyber Security", sem:1, students:57, status:"Active",
    subjects:["Python Programming","Digital Fundamentals"],
    teachers:[{name:"Dr. Andal V",subject:"Python Programming"},{name:"Mr. Sanjay",subject:"Digital Fundamentals"}] },
  { id:5,  name:"S3 BCA AI", program:"BCA", spec:"Artificial Intelligence", sem:3, students:56, status:"Active",
    subjects:["Computer Networks","Operating Systems","Deep Learning","Python Programming"],
    teachers:[{name:"Mr. Sameeran",subject:"Computer Networks"},{name:"Ms. Soumya K",subject:"Operating Systems"},{name:"Dr. Hari Narayanan",subject:"Deep Learning"},{name:"Mr. Joseph James",subject:"Python Programming"}] },
  { id:6,  name:"S3 BCA CS", program:"BCA", spec:"Cyber Security", sem:3, students:55, status:"Active",
    subjects:["Computer Networks","Operating Systems","Database Management Systems","Python Programming"],
    teachers:[{name:"Dr. Spurgen Ratheash",subject:"Computer Networks"},{name:"Dr. Sruthi",subject:"Operating Systems"},{name:"Dr. Hari Narayanan",subject:"Database Management Systems"},{name:"Dr. Meenu Suresh",subject:"Python Programming"}] },
  { id:7,  name:"S3 BCA DA", program:"BCA", spec:"Data Analytics", sem:3, students:54, status:"Active",
    subjects:["Database Management Systems","Python Programming","Operating Systems"],
    teachers:[{name:"Dr. Nisha",subject:"Database Management Systems"},{name:"Dr. Hari Narayanan",subject:"Python Programming"},{name:"Ms. Soumya K",subject:"Operating Systems"}] },
  { id:8,  name:"S5 BCA AI", program:"BCA", spec:"Artificial Intelligence", sem:5, students:52, status:"Active",
    subjects:["Generative AI","Deep Learning","Natural Language Processing","Machine Learning"],
    teachers:[{name:"Mr. Sameeran",subject:"Generative AI"},{name:"Dr. Rajeev",subject:"Deep Learning"},{name:"Dr. Nisha",subject:"Natural Language Processing"},{name:"Mr. Joseph James",subject:"Machine Learning"}] },
  { id:9,  name:"S5 BCA CS", program:"BCA", spec:"Cyber Security", sem:5, students:50, status:"Active",
    subjects:["Penetration Testing","Cryptography","Cyber Forensics","Digital Forensics"],
    teachers:[{name:"Dr. Andal V",subject:"Penetration Testing"},{name:"Ms. Soumya K",subject:"Cryptography"},{name:"Mr. Vipin",subject:"Cyber Forensics"},{name:"Mr. Vipin",subject:"Digital Forensics"}] },
  { id:10, name:"S5 BCA DA+Gen", program:"BCA", spec:"Data Analytics", sem:5, students:51, status:"Active",
    subjects:["Data Warehousing & Mining","R Programming","Generative AI"],
    teachers:[{name:"Dr. Spurgen Ratheash",subject:"Data Warehousing & Mining"},{name:"Dr. Meenu Suresh",subject:"R Programming"},{name:"Mr. Sameeran",subject:"Generative AI"}] },
];

const PROGRAMS  = ["All Programs",  "BCA"];
const SEMESTERS = ["All Semesters", "1", "3", "5"];

/* avatar initials + color */
const AVATAR_COLORS = ["#2563eb","#16a34a","#7c3aed","#d97706","#dc2626","#0891b2"];
function avatarColor(name) { return AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length]; }
function initials(name)    { return name.split(" ").slice(0,2).map(w=>w[0]).join(""); }

const DETAIL_TABS = ["Overview","Teachers","Subjects","Timetable"];

export default function Classes() {
  const navigate = useNavigate();
  const [search,      setSearch]      = useState("");
  const [filterProg,  setFilterProg]  = useState("All Programs");
  const [filterSem,   setFilterSem]   = useState("All Semesters");
  const [selectedId,  setSelectedId]  = useState(null);
  const [detailTab,   setDetailTab]   = useState("Overview");

  const selected = CLASS_DATA.find(c => c.id === selectedId);

  const filtered = CLASS_DATA.filter(c => {
    if (filterProg !== "All Programs"  && c.program !== filterProg) return false;
    if (filterSem  !== "All Semesters" && String(c.sem) !== filterSem) return false;
    if (search && !c.name.toLowerCase().includes(search.toLowerCase()) &&
        !c.spec.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const sem1Count = CLASS_DATA.filter(c => c.sem === 1).length;
  const sem3Count = CLASS_DATA.filter(c => c.sem === 3).length;
  const sem5Count = CLASS_DATA.filter(c => c.sem === 5).length;

  return (
    <div className="cls-page">
      {/* ── HEADER ── */}
      <div className="cls-header">
        <div>
          <h1 className="cls-title">Classes</h1>
          <p className="cls-subtitle">Manage department classes, sections and academic programs.</p>
        </div>
        <button className="btn-add-class"><IcPlus size={15} /> Add Class</button>
      </div>

      {/* ── STAT CARDS ── */}
      <div className="cls-stats">
        <ClsStatCard tone="blue"   Icon={IcUsers} value={CLASS_DATA.length} label="Total Classes" />
        <ClsStatCard tone="green"  Icon={IcGrad}  value={sem1Count}         label="Semester 1" />
        <ClsStatCard tone="purple" Icon={IcUsers} value={sem3Count}         label="Semester 3" />
        <ClsStatCard tone="amber"  Icon={IcBook}  value={sem5Count}         label="Semester 5" />
      </div>

      {/* ── FILTERS ── */}
      <div className="cls-filters">
        <div className="cls-filter-group">
          <label>Program</label>
          <div className="cls-select-wrap">
            <select value={filterProg} onChange={e => setFilterProg(e.target.value)}>
              {PROGRAMS.map(p => <option key={p}>{p}</option>)}
            </select>
            <IcChevron size={13} />
          </div>
        </div>
        <div className="cls-filter-group">
          <label>Semester</label>
          <div className="cls-select-wrap">
            <select value={filterSem} onChange={e => setFilterSem(e.target.value)}>
              {SEMESTERS.map(s => <option key={s}>{s}</option>)}
            </select>
            <IcChevron size={13} />
          </div>
        </div>
        <div className="cls-filter-group" style={{ flex:1 }}>
          <label>Search</label>
          <div className="cls-search-wrap">
            <IcSearch size={14} />
            <input
              type="text"
              placeholder="Search classes..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && <button className="cls-search-clear" onClick={() => setSearch("")}><IcX size={13} /></button>}
          </div>
        </div>
        <div className="cls-filter-group">
          <label>Status</label>
          <div className="cls-select-wrap">
            <select defaultValue="Active"><option>Active</option><option>Inactive</option></select>
            <IcChevron size={13} />
          </div>
        </div>
      </div>

      {/* ── TABLE + DETAIL PANEL ── */}
      <div className={"cls-main" + (selectedId ? " panel-open" : "")}>
        {/* Table card */}
        <div className="card cls-table-card">
          <div className="tbl-wrap">
            <table className="cls-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Class</th>
                  <th>Program</th>
                  <th>Specialization</th>
                  <th>Semester</th>
                  <th>Students</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((cls, i) => (
                  <tr
                    key={cls.id}
                    className={selectedId === cls.id ? "cls-row selected" : "cls-row"}
                    onClick={() => { setSelectedId(cls.id); setDetailTab("Overview"); }}
                  >
                    <td className="td-num">{i + 1}</td>
                    <td>
                      <span className="cls-name-link">{cls.name}</span>
                    </td>
                    <td>
                      <span className={"prog-badge prog-" + cls.program.toLowerCase().replace(".","")}>
                        {cls.program}
                      </span>
                    </td>
                    <td style={{ color:"var(--gray-600)", fontSize:13 }}>{cls.spec}</td>
                    <td style={{ fontSize:13 }}>{cls.sem ?? "—"}</td>
                    <td style={{ fontSize:13 }}>{cls.students ?? "—"}</td>
                    <td><span className="pill green" style={{fontSize:11}}>Active</span></td>
                    <td onClick={e => e.stopPropagation()}>
                      <div className="cls-actions">
                        <button className="btn-view" onClick={() => { setSelectedId(cls.id); setDetailTab("Overview"); }}>
                          <IcEye size={13}/> View
                        </button>
                        <button className="btn-view"><IcEdit size={13}/> Edit</button>
                        <button className="btn-icon-only"><IcMore size={14}/></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={8} className="empty-state">No classes match the current filters.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── DETAIL PANEL ── */}
        {selected && (
          <div className="cls-detail-panel">
            {/* Panel header */}
            <div className="cdp-head">
              <div className="cdp-head-left">
                <div className="cdp-icon"><IcGrad size={20} /></div>
                <div>
                  <div className="cdp-name">{selected.name}</div>
                  <div className="cdp-prog">{selected.program} · {selected.spec}</div>
                </div>
                <span className="pill green" style={{fontSize:11,marginLeft:8}}>Active</span>
              </div>
              <button className="drawer-close" onClick={() => setSelectedId(null)}><IcX size={17}/></button>
            </div>

            {/* Detail tabs */}
            <div className="cdp-tabs">
              {DETAIL_TABS.map(t => (
                <button key={t} className={"cdp-tab" + (detailTab===t?" active":"")} onClick={() => setDetailTab(t)}>{t}</button>
              ))}
            </div>

            <div className="cdp-body">
              {detailTab === "Overview" && (
                <>
                  {/* Info grid */}
                  <div className="cdp-info-grid">
                    {[
                      [IcGrad,     "Program",       selected.program],
                      [IcBook,     "Specialization",selected.spec],
                      [IcCalendar, "Semester",      selected.sem ?? "—"],
                      [IcUsers,    "Students",      selected.students ?? "—"],
                      [IcCalendar, "Academic Year", "2026 - 2027"],
                    ].map(([Icon,label,val]) => (
                      <div key={label} className="cdp-info-row">
                        <span className="cdp-info-icon"><Icon size={14}/></span>
                        <span className="cdp-info-label">{label}</span>
                        <span className="cdp-info-val">{val}</span>
                      </div>
                    ))}
                  </div>

                  {/* Assigned Teachers */}
                  <div className="cdp-section-head">
                    <span>Assigned Teachers ({selected.teachers.length})</span>
                    <span className="view-all">View all →</span>
                  </div>
                  <div className="cdp-teachers">
                    {selected.teachers.map(t => (
                      <div key={t.name} className="cdp-teacher-row">
                        <span className="cdp-avatar" style={{background: avatarColor(t.name)}}>
                          {initials(t.name)}
                        </span>
                        <div>
                          <div className="cdp-teacher-name">{t.name}</div>
                          <div className="cdp-teacher-sub">{t.subject}</div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Subjects */}
                  <div className="cdp-section-head" style={{marginTop:16}}>
                    <span>Subjects ({selected.subjects.length})</span>
                    <span className="view-all">View all →</span>
                  </div>
                  <div className="cdp-subjects">
                    {selected.subjects.map(s => (
                      <span key={s} className="cdp-subject-tag">{s}</span>
                    ))}
                  </div>
                </>
              )}

              {detailTab === "Teachers" && (
                <div className="cdp-teachers">
                  {selected.teachers.map(t => (
                    <div key={t.name} className="cdp-teacher-row">
                      <span className="cdp-avatar" style={{background: avatarColor(t.name)}}>{initials(t.name)}</span>
                      <div style={{flex:1}}>
                        <div className="cdp-teacher-name">{t.name}</div>
                        <div className="cdp-teacher-sub">{t.subject}</div>
                      </div>
                      <span className="pill green" style={{fontSize:11}}>Active</span>
                    </div>
                  ))}
                </div>
              )}

              {detailTab === "Subjects" && (
                <div style={{display:"flex",flexWrap:"wrap",gap:8,marginTop:4}}>
                  {selected.subjects.map(s => (
                    <span key={s} className="cdp-subject-tag" style={{fontSize:13,padding:"6px 14px"}}>{s}</span>
                  ))}
                </div>
              )}

              {detailTab === "Timetable" && (
                <div className="empty-state" style={{padding:"32px 0"}}>
                  <IcTimetable size={32} />
                  <p style={{marginTop:10}}>Timetable for {selected.name}</p>
                  <button style={{marginTop:12,fontSize:13}} onClick={() => navigate("/timetable")}>
                    View Full Timetable
                  </button>
                </div>
              )}
            </div>

            {/* Panel footer actions */}
            <div className="cdp-footer">
              <button className="cdp-btn-edit"><IcEdit size={14}/> Edit Class</button>
              <button className="cdp-btn-tt" onClick={() => navigate("/timetable")}><IcTimetable size={14}/> View Timetable</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ClsStatCard({ tone, Icon, value, label }) {
  return (
    <div className={"stat-card cls-stat-" + tone}>
      <div className={"stat-icon-wrap " + tone}><Icon size={22}/></div>
      <div className="stat-body">
        <div className={"stat-num" + (tone==="blue"?"":" "+tone)}>{value}</div>
        <div className="stat-lbl">{label}</div>
      </div>
      <span className="stat-arrow">›</span>
    </div>
  );
}
