-- Extend the appearance choices while preserving vehicle IDs and passenger references.
ALTER TABLE vehicles ADD COLUMN appearance_v9 TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance_v9 IN ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun', 'mega'));
UPDATE vehicles SET appearance_v9 = appearance;
ALTER TABLE vehicles DROP COLUMN appearance;
ALTER TABLE vehicles RENAME COLUMN appearance_v9 TO appearance;
PRAGMA user_version = 9;
