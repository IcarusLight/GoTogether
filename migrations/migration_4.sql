ALTER TABLE vehicles ADD COLUMN appearance TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance IN ('phantom', 'tricycle', 'su7'));
PRAGMA user_version = 4;
