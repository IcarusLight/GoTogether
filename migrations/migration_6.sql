-- Existing SU7 vehicles use Capri Blue; other models retain their original artwork.
ALTER TABLE vehicles ADD COLUMN color TEXT NOT NULL DEFAULT 'default';
PRAGMA user_version = 6;
