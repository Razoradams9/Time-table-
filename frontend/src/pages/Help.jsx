import { useMemo, useState } from "react";
import { useAuth } from "../auth.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { Icon, icons } from "../components/Icons.jsx";

// Help & Support centre. Layout follows patterns common to well-known help
// centres (Intercom / Zendesk / Notion / Slack / GitHub Docs): a search bar
// over a searchable FAQ, topic quick-start cards, collapsible FAQ accordions,
// and a contact/support block. Content reflects this app's real features.

const TOPICS = [
  {
    icon: "timetable",
    title: "Timetable",
    body: "View the weekly timetable by teacher or by class. HODs can generate and approve a new version.",
  },
  {
    icon: "leaves",
    title: "Leaves",
    body: "Register a leave for an upcoming day; substitutes are assigned automatically for affected periods.",
  },
  {
    icon: "substitutions",
    title: "Substitutions",
    body: "See daily coverage, reassign a substitute, or view AI suggestions for uncovered periods.",
    hod: true,
  },
  {
    icon: "teachers",
    title: "Teacher accounts",
    body: "Add staff, reset passwords, and enable or disable access from the Teachers page.",
    hod: true,
  },
  {
    icon: "reports",
    title: "Reports",
    body: "Review substitution fairness across staff and export the figures as CSV or PDF.",
    hod: true,
  },
  {
    icon: "messages",
    title: "Notifications",
    body: "Assignments, cancellations, and coverage alerts arrive in your in-app inbox.",
  },
];

const FAQS = [
  {
    q: "How do I view my timetable?",
    a: "Open Timetable from the sidebar. Use the Teacher / Class toggle to switch views, then pick a name from the dropdown. The grid shows every period, with lab blocks marked LAB.",
  },
  {
    q: "How do I register a leave?",
    a: "Go to Leaves, choose the date (future dates only), pick full-day or specific periods, add an optional reason, and submit. The system immediately finds and assigns substitutes for the periods you'd have taught.",
    tags: ["leave", "absent", "holiday"],
  },
  {
    q: "Can I cancel a leave I already registered?",
    a: "Yes, as long as the leave date hasn't passed. Cancelling a leave reverts any substitutions that were created for it, and the affected substitutes are notified.",
    tags: ["leave", "cancel"],
  },
  {
    q: "How are substitutes chosen?",
    a: "A rule-based engine ranks free teachers by subject and department match, current workload, and fairness. Same-department teachers are preferred, but any available teacher is eligible. The assignment is automatic and auditable, and an HOD can override it.",
    tags: ["substitute", "cover", "engine"],
  },
  {
    q: "A period is uncovered. What can I do?",
    a: "On the Substitutions page, open the uncovered period to see ranked candidates and AI suggestions (swap, merge, or self-study). HODs can manually assign any teacher who is genuinely free that slot.",
    hod: true,
    tags: ["uncovered", "substitute"],
  },
  {
    q: "How do I generate or approve a timetable?",
    a: "On the Timetable page, an HOD clicks Generate to build a conflict-free schedule, then Approve to lock it as the active base timetable. Only the approved version is shown across the app.",
    hod: true,
    tags: ["generate", "approve", "timetable"],
  },
  {
    q: "How do I add a teacher or reset a password?",
    a: "Open Teachers (HOD only). Add teacher creates an account with a one-time temporary password shown once — hand it over securely. Reset pw issues a fresh temporary password; the teacher must set their own on next login.",
    hod: true,
    tags: ["account", "password", "teacher"],
  },
  {
    q: "How do I export reports?",
    a: "On the Reports page, pick a date range to see each teacher's substitution count, then use the CSV or PDF buttons to download the figures.",
    hod: true,
    tags: ["report", "export", "csv", "pdf"],
  },
  {
    q: "Where do notifications come from?",
    a: "The system notifies you when a substitution is assigned to you, cancelled, or when a period you'd have taught is covered. HODs are also alerted to new leaves and uncovered periods. Check the bell icon or the Messages page.",
    tags: ["notification", "alert", "inbox"],
  },
  {
    q: "I can't reach the server — what now?",
    a: "The app signs in automatically; if it can't connect it shows a retry screen. Make sure the backend is running, then click Try again. If it persists, contact your administrator.",
    tags: ["error", "server", "login"],
  },
];

function Chevron({ open }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ transition: "transform 0.2s ease", transform: open ? "rotate(180deg)" : "none" }}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

export default function Help() {
  const { user } = useAuth();
  const isHod = user.role === "HOD";
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(null);

  const q = query.trim().toLowerCase();

  const visibleTopics = TOPICS.filter((t) => !t.hod || isHod);

  const faqs = useMemo(() => {
    const scoped = FAQS.filter((f) => !f.hod || isHod);
    if (!q) return scoped;
    return scoped.filter((f) => {
      const hay = `${f.q} ${f.a} ${(f.tags || []).join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
  }, [q, isHod]);

  return (
    <>
      <PageHeader
        badge="Help centre"
        title="Help & Support"
        subtitle="Guides, answers to common questions, and how to reach us."
      />

      {/* Search */}
      <div className="card help-search">
        <Icon path={icons.help} size={20} />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search help articles — e.g. 'register a leave', 'substitute', 'export'"
          aria-label="Search help"
        />
      </div>

      {/* Topic quick-start cards */}
      {!q && (
        <>
          <h3 className="help-section-title">Browse by topic</h3>
          <div className="help-topics">
            {visibleTopics.map((t) => (
              <div className="help-topic" key={t.title}>
                <span className="help-topic-ic">
                  <Icon path={icons[t.icon]} size={22} />
                </span>
                <div>
                  <div className="help-topic-title">{t.title}</div>
                  <p>{t.body}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* FAQ accordion */}
      <h3 className="help-section-title">
        {q ? `Results for “${query}”` : "Frequently asked questions"}
      </h3>
      <div className="card help-faq">
        {faqs.length === 0 ? (
          <p className="sub" style={{ margin: 0 }}>
            No articles match “{query}”. Try a different word, or contact support below.
          </p>
        ) : (
          faqs.map((f, i) => {
            const isOpen = open === f.q;
            return (
              <div className={"help-faq-item" + (isOpen ? " open" : "")} key={f.q}>
                <button
                  type="button"
                  className="help-faq-q"
                  aria-expanded={isOpen}
                  onClick={() => setOpen(isOpen ? null : f.q)}
                >
                  <span>{f.q}</span>
                  <Chevron open={isOpen} />
                </button>
                {isOpen && <div className="help-faq-a">{f.a}</div>}
                {i < faqs.length - 1 && <div className="help-faq-sep" />}
              </div>
            );
          })
        )}
      </div>

      {/* Contact / support */}
      <h3 className="help-section-title">Still need help?</h3>
      <div className="help-contact">
        <div className="card help-contact-card">
          <span className="help-topic-ic">
            <Icon path={icons.messages} size={22} />
          </span>
          <div className="help-topic-title">Email support</div>
          <p>Reach the department admin for account or scheduling issues.</p>
          <a className="help-link" href="mailto:support@college.edu">
            support@college.edu
          </a>
        </div>
        <div className="card help-contact-card">
          <span className="help-topic-ic">
            <Icon path={icons.teachers} size={22} />
          </span>
          <div className="help-topic-title">Ask your HOD</div>
          <p>Account changes, password resets, and overrides are handled by your HOD / administrator.</p>
        </div>
        <div className="card help-contact-card">
          <span className="help-topic-ic">
            <Icon path={icons.bell} size={22} />
          </span>
          <div className="help-topic-title">Check notifications</div>
          <p>Many updates (assignments, cancellations, coverage) arrive in your in-app inbox.</p>
        </div>
      </div>
    </>
  );
}
