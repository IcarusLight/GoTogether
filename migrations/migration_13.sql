-- Add the droplet while preserving vehicle IDs, colors and passenger references.
ALTER TABLE vehicles ADD COLUMN appearance_v13 TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance_v13 IN ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun', 'mega', 'ct5', 'han', 'mazda929', 'droplet'));
UPDATE vehicles SET appearance_v13 = appearance;
ALTER TABLE vehicles DROP COLUMN appearance;
ALTER TABLE vehicles RENAME COLUMN appearance_v13 TO appearance;
PRAGMA user_version = 13;
