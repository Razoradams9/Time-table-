import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import MyTimetable from "./pages/MyTimetable.jsx";
import TimetableViews from "./pages/TimetableViews.jsx";
import Leaves from "./pages/Leaves.jsx";
import Notifications from "./pages/Notifications.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import TeacherDashboard from "./pages/TeacherDashboard.jsx";
import Substitutions from "./pages/Substitutions.jsx";
import Fairness from "./pages/Fairness.jsx";
import Teachers from "./pages/Teachers.jsx";
import Help from "./pages/Help.jsx";
import Courses from "./pages/Courses.jsx";
import Compensations from "./pages/Compensations.jsx";
import Login from "./pages/Login.jsx";
import ChangePassword from "./pages/ChangePassword.jsx";

// Not signed in -> Login (remembering where the user was heading).
// `hodOnly` pages send teachers back to their dashboard.
function Protected({ children, hodOnly }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (hodOnly && user.role !== "HOD") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="spinner">Loading…</div>;

  const isHod = user?.role === "HOD";

  // First sign-in after a reset: nothing else is reachable until it is changed.
  if (user?.must_change_password) {
    return (
      <Routes>
        <Route path="/change-password" element={<ChangePassword forced />} />
        <Route path="*" element={<Navigate to="/change-password" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={isHod ? <Dashboard /> : <TeacherDashboard />} />
        <Route path="/timetable" element={<TimetableViews />} />
        <Route path="/courses" element={<Courses />} />
        <Route
          path="/my-timetable"
          element={
            <Protected hodOnly>
              <MyTimetable />
            </Protected>
          }
        />
        <Route path="/leaves" element={<Leaves />} />
        <Route path="/compensations" element={<Compensations />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/change-password" element={<ChangePassword />} />
        <Route path="/help" element={<Help />} />
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
