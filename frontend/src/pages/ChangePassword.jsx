import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import PageHeader from "../components/PageHeader.jsx";

export default function ChangePassword({ forced = false }) {
  const { user, logout, refreshUser, branding } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const rules = [
    { ok: next.length >= 8, text: "At least 8 characters" },
    { ok: /[A-Za-z]/.test(next), text: "Contains a letter" },
    { ok: /\d/.test(next), text: "Contains a number" },
    { ok: next !== "" && next !== current, text: "Different from the current password" },
    { ok: next !== "" && next === confirm, text: "Both new passwords match" },
  ];
  const valid = current !== "" && rules.every((r) => r.ok);

  async function onSubmit(e) {
    e.preventDefault();
    if (!valid || busy) return;
    setBusy(true);
    setError("");
    try {
      await api.changePassword(current, next);
      await refreshUser();
      setDone(true);
      if (forced) navigate("/", { replace: true });
      else {
        setCurrent("");
        setNext("");
        setConfirm("");
      }
    } catch (ex) {
      setError(ex.message);
    } finally {
      setBusy(false);
    }
  }

  const form = (
    <form onSubmit={onSubmit}>
      {/* Lets password managers associate the new password with this account. */}
      <input type="text" name="username" autoComplete="username" value={user.email || ""} readOnly hidden />
      {error && <p className="login-error" role="alert">{error}</p>}
      {done && !forced && <p className="login-notice" role="status">Password changed.</p>}

      <label htmlFor="cp-current">Current password</label>
      <input id="cp-current" type="password" autoComplete="current-password" required
        value={current} onChange={(e) => setCurrent(e.target.value)} />

      <label htmlFor="cp-new">New password</label>
      <input id="cp-new" type="password" autoComplete="new-password" required
        value={next} onChange={(e) => setNext(e.target.value)} aria-describedby="cp-rules" />

      <label htmlFor="cp-confirm">Confirm new password</label>
      <input id="cp-confirm" type="password" autoComplete="new-password" required
        value={confirm} onChange={(e) => setConfirm(e.target.value)} />

      <ul id="cp-rules" className="pw-rules">
        {rules.map((r) => (
          <li key={r.text} className={r.ok ? "ok" : ""}>
            <span aria-hidden="true">{r.ok ? "✓" : "○"}</span> {r.text}
            <span className="sr-only">{r.ok ? " (met)" : " (not met)"}</span>
          </li>
        ))}
      </ul>

      <button type="submit" className="login-submit" disabled={!valid || busy}>
        {busy ? "Saving…" : "Change password"}
      </button>
    </form>
  );

  if (!forced) {
    return (
      <div>
        <PageHeader title="Change password" subtitle="Choose a new password for your account." />
        <div className="card change-pw-card">{form}</div>
      </div>
    );
  }

  return (
    <div className="login-shell">
      <main className="login-card" aria-labelledby="cp-title">
        <img className="login-logo" src="/jain-logo-light.png" alt="Jain Deemed-to-be University, Kochi" />
        <div className="dept-label">{branding.product_name}</div>
        <h1 id="cp-title" className="login-title">Set a new password</h1>
        <p className="login-sub">
          Hi {user.name}, you need to choose a new password before continuing.
        </p>
        {form}
        <button type="button" className="ghost login-signout" onClick={logout}>
          Sign out
        </button>
      </main>
    </div>
  );
}
