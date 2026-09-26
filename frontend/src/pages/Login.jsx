import { useState } from "react";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { login, branding } = useAuth();
  const [email, setEmail] = useState("hod@college.edu");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
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
        <h2>Welcome back</h2>
        <p className="sub">Sign in to the {branding.product_name}.</p>
        <form onSubmit={submit}>
          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="hint">
          <strong>Demo logins</strong> (password: <code>password123</code>)
          <br />
          HOD: hod@college.edu
          <br />
          Teacher: asha@college.edu, bala@college.edu, deepak@college.edu
        </div>
      </div>
    </div>
  );
}
