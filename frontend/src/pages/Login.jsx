import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { user, login, branding, sessionMessage, clearSessionMessage } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from;
  const target = from ? `${from.pathname || "/"}${from.search || ""}` : "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const emailRef = useRef(null);

  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  if (user) return <Navigate to={target} replace />;

  async function onSubmit(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    clearSessionMessage();
    try {
      await login(email.trim(), password);
      navigate(target, { replace: true });
    } catch (ex) {
      setError(ex.message || "Sign-in failed. Please try again.");
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <main className="login-card" aria-labelledby="login-title">
        <img className="login-logo" src="/jain-logo-light.png" alt="Jain Deemed-to-be University, Kochi" />
        <div className="dept-label">{branding.product_name}</div>
        <h1 id="login-title" className="login-title">Sign in</h1>
        <p className="login-sub">{branding.department_name}</p>

        {sessionMessage && !error && (
          <p className="login-notice" role="status">{sessionMessage}</p>
        )}
        {error && (
          <p className="login-error" role="alert">{error}</p>
        )}

        <form onSubmit={onSubmit} noValidate={false}>
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            ref={emailRef}
            type="email"
            name="username"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@college.edu"
          />

          <label htmlFor="login-password">Password</label>
          <div className="pw-field">
            <input
              id="login-password"
              type={show ? "text" : "password"}
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              className="pw-toggle ghost"
              onClick={() => setShow((v) => !v)}
              aria-pressed={show}
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? "Hide" : "Show"}
            </button>
          </div>

          <button type="submit" className="login-submit" disabled={busy || !email || !password}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {/* Alternative sign-in methods (e.g. a "Sign in with Google" button) go here. */}
        <div className="login-alt" />

        <p className="login-foot">
          {branding.institution_name} · {branding.institution_subtitle}
        </p>
      </main>
    </div>
  );
}
