-- Replace only the appearance column so vehicle IDs and passenger references stay intact.
ALTER TABLE vehicles ADD COLUMN appearance_v5 TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance_v5 IN ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage'));
UPDATE vehicles SET appearance_v5 = appearance;
ALTER TABLE vehicles DROP COLUMN appearance;
ALTER TABLE vehicles RENAME COLUMN appearance_v5 TO appearance;
PRAGMA user_version = 5;
