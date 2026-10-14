CREATE TABLE registrations_v2 (
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
INSERT INTO registrations_v2(event_id, name, mode, vehicle_id, note, revision)
    SELECT event_id, name, mode, vehicle_id, note, revision FROM registrations;
DROP TABLE registrations;
ALTER TABLE registrations_v2 RENAME TO registrations;
CREATE INDEX registration_vehicle ON registrations(vehicle_id, mode);
PRAGMA user_version = 2;
