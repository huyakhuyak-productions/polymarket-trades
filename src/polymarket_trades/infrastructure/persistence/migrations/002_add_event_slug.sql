INSERT OR IGNORE INTO schema_version (version) VALUES (2);

ALTER TABLE opportunities ADD COLUMN event_slug TEXT NOT NULL DEFAULT '';
ALTER TABLE positions ADD COLUMN event_slug TEXT NOT NULL DEFAULT '';
