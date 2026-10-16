import { useEffect, useState } from "react";
import { api } from "../api";
import PageHeader from "../components/PageHeader.jsx";
import { SkeletonRows } from "../components/Skeleton.jsx";

export default function Notifications() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setNotes(await api.notifications());
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  async function markAll() {
    await api.markAllRead();
    await load();
  }
  async function markOne(id) {
    await api.markRead(id);
    await load();
  }

  if (loading) {
    return (
      <>
        <PageHeader badge="Inbox" title="Notifications" subtitle="Loading…" />
        <div className="card">
          <SkeletonRows rows={5} />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        badge="Inbox"
        title="Notifications"
        subtitle="Assignments, cancellations, and coverage alerts."
      >
        {notes.some((n) => !n.is_read) && (
          <button className="ghost" onClick={markAll}>
            Mark all read
          </button>
        )}
      </PageHeader>
      <div className="card">
      {notes.length === 0 ? (
        <p className="sub">You're all caught up.</p>
      ) : (
        notes.map((n) => (
          <div key={n.id} className={`note-item ${n.is_read ? "" : "unread"}`}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <div>
                <div className="t">
                  {!n.is_read && <span className="pill blue" style={{ marginRight: 6 }}>New</span>}
                  {n.title}
                </div>
                <div className="b">{n.body}</div>
                <div className="d">{new Date(n.created_at).toLocaleString()}</div>
              </div>
              {!n.is_read && (
                <button className="ghost small" onClick={() => markOne(n.id)}>
                  Mark read
                </button>
              )}
            </div>
          </div>
        ))
      )}
      </div>
    </>
  );
}
