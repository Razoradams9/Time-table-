import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import MyTimetable from "./pages/MyTimetable.jsx";
import Leaves from "./pages/Leaves.jsx";
import Notifications from "./pages/Notifications.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Substitutions from "./pages/Substitutions.jsx";
import Fairness from "./pages/Fairness.jsx";
import Teachers from "./pages/Teachers.jsx";
import ChangePassword from "./pages/ChangePassword.jsx";

function Protected({ children, hodOnly }) {
  const { user, loading, mustChangePassword } = useAuth();
  if (loading) return <div className="spinner">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  // Force the password change before any protected content is reachable.
  if (mustChangePassword) return <Navigate to="/change-password" replace />;
  if (hodOnly && user.role !== "HOD") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user, loading, mustChangePassword } = useAuth();
  if (loading) return <div className="spinner">Loading…</div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route
        path="/change-password"
        element={user ? <ChangePassword /> : <Navigate to="/login" replace />}
      />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/timetable" element={<MyTimetable />} />
        <Route path="/leaves" element={<Leaves />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route
          path="/teachers"
          element={
            <Protected hodOnly>
              <Teachers />
            </Protected>
          }
        />
        <Route
          path="/substitutions"
          element={
            <Protected hodOnly>
              <Substitutions />
            </Protected>
          }
        />
        <Route
          path="/fairness"
          element={
            <Protected hodOnly>
              <Fairness />
            </Protected>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
