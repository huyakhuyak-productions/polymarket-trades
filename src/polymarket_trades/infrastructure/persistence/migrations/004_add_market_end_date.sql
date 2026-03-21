INSERT OR IGNORE INTO schema_version (version) VALUES (4);

ALTER TABLE positions ADD COLUMN market_end_date TEXT;
