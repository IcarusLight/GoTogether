-- Add Mazda 929 while preserving vehicle IDs, colors and passenger references.
ALTER TABLE vehicles ADD COLUMN appearance_v12 TEXT NOT NULL DEFAULT 'su7'
    CHECK (appearance_v12 IN ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun', 'mega', 'ct5', 'han', 'mazda929'));
UPDATE vehicles SET appearance_v12 = appearance;
ALTER TABLE vehicles DROP COLUMN appearance;
ALTER TABLE vehicles RENAME COLUMN appearance_v12 TO appearance;
PRAGMA user_version = 12;
