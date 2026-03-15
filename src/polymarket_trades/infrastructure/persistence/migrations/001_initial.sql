CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_type TEXT NOT NULL, market_id TEXT NOT NULL, token_id TEXT NOT NULL,
    event_title TEXT NOT NULL, expected_profit TEXT NOT NULL, entry_price TEXT NOT NULL,
    detected_at TEXT NOT NULL, extra_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY, opportunity_type TEXT NOT NULL, market_id TEXT NOT NULL,
    token_id TEXT NOT NULL, side TEXT NOT NULL, event_title TEXT NOT NULL,
    entry_price TEXT NOT NULL, quantity TEXT NOT NULL, detected_at TEXT NOT NULL,
    entry_time TEXT NOT NULL, current_price TEXT NOT NULL, resolution_outcome TEXT,
    exit_price TEXT, pnl TEXT, fees_estimated TEXT NOT NULL, mode TEXT NOT NULL,
    status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_market ON positions(market_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_dedup ON opportunities(strategy_type, market_id, token_id);
