import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import MyTimetable from "./pages/MyTimetable.jsx";
import TimetableViews from "./pages/TimetableViews.jsx";
import Leaves from "./pages/Leaves.jsx";
import Notifications from "./pages/Notifications.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Substitutions from "./pages/Substitutions.jsx";
import Fairness from "./pages/Fairness.jsx";
import Teachers from "./pages/Teachers.jsx";

function Protected({ children, hodOnly }) {
  const { user } = useAuth();
  if (hodOnly && user.role !== "HOD") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="spinner">Loading…</div>;

  // There is no login screen. The app signs in automatically on load; if that
  // fails (usually the backend is unreachable) show a retry screen instead.
  if (!user) {
    return (
      <div className="spinner">
        <p>Can't reach the server. Please check that the backend is running.</p>
        <button type="button" onClick={() => window.location.reload()}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/timetable" element={<TimetableViews />} />
        <Route path="/my-timetable" element={<MyTimetable />} />
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
