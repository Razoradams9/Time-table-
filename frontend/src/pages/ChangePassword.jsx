import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";

export default function ChangePassword() {
  const { branding, mustChangePassword, clearMustChangePassword, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const forced = mustChangePassword;

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (next !== confirm) {
      setError("New password and confirmation do not match.");
      return;
    }
    if (next.length < 8 || !/[a-zA-Z]/.test(next) || !/\d/.test(next)) {
      setError("Password must be at least 8 characters and include a letter and a number.");
      return;
    }
    setBusy(true);
    try {
      await api.changePassword(current, next);
      clearMustChangePassword();
      setDone(true);
      setTimeout(() => navigate("/", { replace: true }), 900);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="card login-card">
        <div className="login-brand">
          <span className="logo-badge">JGi</span>
          <div>
            <div className="login-inst">{branding.institution_name}</div>
            <div className="login-inst-sub">{branding.department_name}</div>
          </div>
        </div>
        <h2>{forced ? "Set a new password" : "Change password"}</h2>
        <p className="sub">
          {forced
            ? "For security, please replace your temporary password before continuing."
            : "Update the password for your account."}
        </p>

        {done ? (
          <div className="success">Password updated. Redirecting…</div>
        ) : (
          <form onSubmit={submit}>
            <div style={{ marginBottom: 12 }}>
              <label>{forced ? "Temporary password" : "Current password"}</label>
              <input
                type="password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>New password</label>
              <input
                type="password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Confirm new password</label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
            {error && <div className="error">{error}</div>}
            <button type="submit" disabled={busy} style={{ width: "100%" }}>
              {busy ? "Updating…" : "Update password"}
            </button>
          </form>
        )}

        {forced && !done && (
          <div className="hint">
            Not you?{" "}
            <button className="linklike" onClick={logout} type="button">
              Log out
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
