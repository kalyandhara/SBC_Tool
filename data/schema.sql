-- SBC Tool database schema
-- Auto-applied on first request if tables don't exist

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_key TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    name TEXT,
    is_default INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_profiles_user_key ON profiles(user_key);
CREATE INDEX IF NOT EXISTS idx_profiles_default ON profiles(user_key, is_default);

CREATE TABLE IF NOT EXISTS habit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_key TEXT NOT NULL,
    habit_type TEXT NOT NULL,
    log_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_habit_logs_user_key ON habit_logs(user_key);
CREATE INDEX IF NOT EXISTS idx_habit_logs_user_date ON habit_logs(user_key, habit_type, log_date);
CREATE UNIQUE INDEX IF NOT EXISTS ux_habit_logs_user_type_date ON habit_logs(user_key, habit_type, log_date);