// Static mock data – no backend required.

export const MOCK_USER = {
  id: 1,
  name: "Dr. Anjana Sharma",
  email: "anjana@college.edu",
  role: "HOD",
  teacher_id: 1,
};

export const MOCK_BRANDING = {
  institution_name: "JGI JAIN",
  institution_subtitle: "Deemed-to-be University",
  department_name: "Department of Computer Applications",
  product_name: "Timetable Management System",
  semester_label: "Even semester | 2026",
};

// Mon=0 … Fri=4, 6 periods per day
const DAYS = 5;
const PERIODS = 6;

export const MOCK_TIME_SLOTS = Array.from({ length: DAYS * PERIODS }, (_, i) => {
  const day = Math.floor(i / PERIODS);
  const period = i % PERIODS;
  const startHour = 9 + period;
  return {
    id: i + 1,
    day_of_week: day,
    period_index: period,
    start_time: `${String(startHour).padStart(2, "0")}:00`,
    end_time: `${String(startHour + 1).padStart(2, "0")}:00`,
  };
});

export const MOCK_TEACHERS = [
  { id: 1, name: "Dr. Anjana Sharma", role: "HOD", email: "anjana@college.edu", max_periods_per_day: 4, is_active: true },
  { id: 2, name: "Prof. Ravi Kumar", role: "TEACHER", email: "ravi@college.edu", max_periods_per_day: 5, is_active: true },
  { id: 3, name: "Ms. Priya Nair", role: "TEACHER", email: "priya@college.edu", max_periods_per_day: 5, is_active: true },
  { id: 4, name: "Mr. Suresh Babu", role: "TEACHER", email: "suresh@college.edu", max_periods_per_day: 5, is_active: true },
  { id: 5, name: "Dr. Meena Pillai", role: "TEACHER", email: "meena@college.edu", max_periods_per_day: 4, is_active: true },
];

const SUBJECT_NAMES = ["Data Structures", "DBMS", "Operating Systems", "Networking", "Python", "Java"];
const CLASS_NAMES = ["MCA-1A", "MCA-1B", "MCA-2A", "MCA-2B"];
const ROOM_NAMES = ["Room 101", "Room 102", "Room 201", "Room 202"];

export const MOCK_CLASSES = CLASS_NAMES.map((name, i) => ({ id: i + 1, name }));

// Timetable entries with nested objects matching what Dashboard/TimetableGrid expects
let entryId = 1;
export const MOCK_TIMETABLE_ENTRIES = [];
MOCK_CLASSES.forEach((cls, ci) => {
  MOCK_TIME_SLOTS.forEach((slot) => {
    const teacher = MOCK_TEACHERS[(ci + slot.period_index + slot.day_of_week) % MOCK_TEACHERS.length];
    const subjectName = SUBJECT_NAMES[(ci + slot.period_index) % SUBJECT_NAMES.length];
    const roomName = ROOM_NAMES[ci % ROOM_NAMES.length];
    MOCK_TIMETABLE_ENTRIES.push({
      id: entryId++,
      // nested shape expected by Dashboard & TimetableGrid
      teacher: { id: teacher.id, name: teacher.name },
      teacher_id: teacher.id,
      teacher_name: teacher.name,
      class_section: { id: cls.id, name: cls.name },
      class_id: cls.id,
      class_name: cls.name,
      subject: { id: ci + 1, name: subjectName },
      subject_name: subjectName,
      room: { id: ci + 1, name: roomName },
      time_slot: slot,
      time_slot_id: slot.id,
      day_of_week: slot.day_of_week,
      period_index: slot.period_index,
      start_time: slot.start_time,
      end_time: slot.end_time,
    });
  });
});

export const MOCK_SUBSTITUTIONS = [
  {
    id: 1,
    period: "P2 (10:00)",
    subject: "Data Structures",
    class_section: "MCA-1A",
    absent_teacher: "Prof. Ravi Kumar",
    substitute_teacher: "Ms. Priya Nair",
    status: "ASSIGNED",
    source: "AUTO",
    explanation: "Ravi Kumar is on approved leave. Priya Nair has a free slot.",
  },
  {
    id: 2,
    period: "P4 (12:00)",
    subject: "DBMS",
    class_section: "MCA-2B",
    absent_teacher: "Mr. Suresh Babu",
    substitute_teacher: null,
    status: "UNCOVERED",
    source: "MANUAL",
    explanation: "No free teacher found automatically. Please assign manually.",
  },
];

export const MOCK_LEAVES = [
  { id: 1, leave_date: "2026-10-15", scope: "FULL_DAY", reason: "Medical", status: "ACTIVE" },
  { id: 2, leave_date: "2026-10-10", scope: "PERIODS", reason: "Workshop", status: "CANCELLED" },
];

export const MOCK_NOTIFICATIONS = [
  {
    id: 1,
    title: "Substitution assigned",
    body: "You are covering DBMS for MCA-2A on Monday P3.",
    is_read: false,
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  },
  {
    id: 2,
    title: "Leave approved",
    body: "Your leave on 2026-10-15 has been recorded. Substitutes assigned.",
    is_read: true,
    created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    title: "Timetable updated",
    body: "A new timetable (v2) has been published for the department.",
    is_read: true,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
];

export const MOCK_OVERVIEW = {
  total_teachers: MOCK_TEACHERS.length,
  present_today: 4,
  absent_today: 1,
  substitutions_today: 2,
};

export const MOCK_ACTIVITY = [
  { id: 1, action: "CREATE", entity: "substitution", actor: "System", detail: "Priya Nair assigned for MCA-1A P2", created_at: new Date(Date.now() - 20 * 60 * 1000).toISOString() },
  { id: 2, action: "CREATE", entity: "leave", actor: "Ravi Kumar", detail: "Leave registered for 2026-10-17", created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() },
  { id: 3, action: "APPROVE", entity: "timetable", actor: "Dr. Anjana Sharma", detail: "Timetable v2 published", created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString() },
];

export const MOCK_FAIRNESS = MOCK_TEACHERS.map((t, i) => ({
  teacher_id: t.id,
  name: t.name,
  substitutions_given: [3, 5, 2, 7, 1][i] || 0,
}));

export const MOCK_CANDIDATES = [
  { teacher_id: 3, name: "Ms. Priya Nair", score: 92, reason: "Free period, same department, low substitution count this week." },
  { teacher_id: 5, name: "Dr. Meena Pillai", score: 78, reason: "Free period, different subject but available." },
];

export const MOCK_SUGGESTIONS = [
  {
    kind: "CANDIDATE",
    description: "Ms. Priya Nair is the best available substitute.",
    explanation: "She has the fewest substitutions this week and is free this period.",
    payload: { substitute_teacher_id: 3 },
  },
];
