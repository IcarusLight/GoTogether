CREATE TABLE events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    creator TEXT NOT NULL,
    is_open INTEGER NOT NULL DEFAULT 1 CHECK (is_open IN (0, 1)),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    driver TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity BETWEEN 0 AND 99),
    departure TEXT NOT NULL,
    departure_time TEXT NOT NULL DEFAULT '',
    plate TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    UNIQUE (event_id, driver),
    UNIQUE (event_id, id)
);

CREATE TABLE registrations (
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('drive', 'ride', 'public', 'other', 'wait')),
    vehicle_id INTEGER,
    note TEXT NOT NULL DEFAULT '',
    revision TEXT NOT NULL,
    pickup TEXT NOT NULL DEFAULT '',
    earliest TEXT NOT NULL DEFAULT '',
    latest TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (event_id, name),
    FOREIGN KEY (event_id, vehicle_id) REFERENCES vehicles(event_id, id) ON DELETE CASCADE,
    CHECK ((mode IN ('drive', 'ride') AND vehicle_id IS NOT NULL)
        OR (mode IN ('public', 'other', 'wait') AND vehicle_id IS NULL))
);
CREATE INDEX registration_vehicle ON registrations(vehicle_id, mode);

CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);
CREATE UNIQUE INDEX reminder_pending ON reminders(event_id, name) WHERE resolved_at IS NULL;
PRAGMA user_version = 3;
