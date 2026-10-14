-- Extend the appearance choices without rebuilding vehicles or changing passenger references.
ALTER TABLE vehicles ADD COLUMN appearance_v8 TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance_v8 IN ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun'));
UPDATE vehicles SET appearance_v8 = appearance;
ALTER TABLE vehicles DROP COLUMN appearance;
ALTER TABLE vehicles RENAME COLUMN appearance_v8 TO appearance;
PRAGMA user_version = 8;
