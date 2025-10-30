// Student types
export interface Student {
  id: number;
  full_name: string;
  gender?: 'male' | 'female'; // Optional until migration
  age: number;
  group_id: number;
  created_at: string;
}

// Group types
export interface Group {
  id: number;
  title: string;
  description?: string;
  created_at: string;
}

export interface GroupWithStudents extends Group {
  students: Student[];
}

// Session types
export interface AttendanceSession {
  id: number;
  group_id: number;
  started_at: string;
  ended_at?: string;
  created_by_tg_user_id: number;
}

// Attendance types
export type AttendanceStatus = 'present' | 'absent';

export interface AttendanceEvent {
  session_id: number;
  student_id: number;
  status: AttendanceStatus;
  timestamp: number;
}

export interface AttendanceBatch {
  events: AttendanceEvent[];
}

// User types
export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export interface UserProfile {
  user_id: number;
  full_name: string;
  role: string;
  teacher_groups: Group[];
}

// Session statistics
export interface SessionStats {
  session_id: number;
  total_students: number;
  present: number;
  absent: number;
  not_marked: number;
}

// Swipe direction
export type SwipeDirection = 'up' | 'down' | 'left' | 'right';

// Card action
export interface CardAction {
  student: Student;
  direction: SwipeDirection;
  status?: AttendanceStatus;
}
