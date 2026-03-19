INSERT OR IGNORE INTO schema_version (version) VALUES (3);

ALTER TABLE opportunities ADD COLUMN side TEXT NOT NULL DEFAULT 'YES';
