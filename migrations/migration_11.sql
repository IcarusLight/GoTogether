-- Add Han while preserving vehicle IDs, colors and passenger references.
ALTER TABLE vehicles ADD COLUMN appearance_v11 TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance_v11 IN ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun', 'mega', 'ct5', 'han'));
UPDATE vehicles SET appearance_v11 = appearance;
ALTER TABLE vehicles DROP COLUMN appearance;
ALTER TABLE vehicles RENAME COLUMN appearance_v11 TO appearance;
PRAGMA user_version = 11;
