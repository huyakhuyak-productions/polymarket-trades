# polymarket-trades

Low-risk automated trading bot for [Polymarket](https://polymarket.com). Implements 3 strategies designed to minimize the chance of losing money, with paper trading as the default mode.

## Strategies

### 1. Near-Certain Outcome Harvester
Buys YES shares on markets priced >= 0.95 where the outcome is essentially decided but hasn't resolved yet. Earns 1-5% per trade with near-certainty.

### 2. Cross-Market Arbitrage Scanner
Finds markets where YES + NO ask prices sum to less than $1.00. Buying both sides guarantees profit on resolution. v1 supports buy-side only.

### 3. Negative Risk Multi-Outcome Discount
On multi-outcome events (3+ outcomes), buys all YES shares when total cost < $1.00. Exactly one outcome resolves to $1.00, so the difference is guaranteed profit.

## Quick Start

```bash
# Install
uv sync

# Run tests
uv run pytest

# Scan for opportunities (paper mode, no trades)
uv run python -m polymarket_trades scan --dry-run

# Run the bot (paper mode — default, safe)
uv run python -m polymarket_trades run --dry-run

# View performance report
uv run python -m polymarket_trades report

# View open positions
uv run python -m polymarket_trades positions
```

## Architecture

Clean Architecture + DDD + TDD.

```
src/polymarket_trades/
├── domain/           # Entities, value objects, ports, services, strategies
│   ├── entities/     # Event (aggregate root), Market, Position
│   ├── value_objects/ # Price, Money, TokenId, Outcome, enums
│   ├── ports/        # Abstract interfaces (EventDiscovery, Pricing, Trading, etc.)
│   ├── services/     # FeeCalculator, RiskManager, Scanner
│   └── strategies/   # 3 detectors + DetectorProtocol
├── application/      # Use cases, scheduler, CLI, DI container
└── infrastructure/   # API clients, SQLite persistence, adapters
```

**Key rule:** Domain layer has zero external dependencies. Infrastructure implements domain ports.

## Configuration

All config via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_INTERVAL_SECONDS` | 300 | Seconds between scan cycles |
| `NEAR_CERTAIN_THRESHOLD` | 0.95 | Min YES price for Strategy 1 |
| `MIN_PROFIT_THRESHOLD` | 0.005 | Min profit per share to consider |
| `MAX_SINGLE_POSITION_PCT` | 0.20 | Max % of capital per position |
| `MAX_TOTAL_EXPOSURE_PCT` | 0.80 | Max % of capital deployed |
| `TOTAL_CAPITAL` | 1000 | Total capital in USDC |
| `TRADE_MODE` | PAPER | PAPER or LIVE |
| `POLYMARKET_PRIVATE_KEY` | | Ethereum wallet key (LIVE only) |

## Paper Trading

`--dry-run` is the **default mode**. The bot identifies opportunities, simulates trades, and tracks paper P&L — without placing real orders. Leave it running to see how much money the strategies would have earned.

To trade with real money, pass `--live` explicitly. This requires a funded Polymarket account and `POLYMARKET_PRIVATE_KEY` set.

## APIs Used

| API | Base URL | Auth | Purpose |
|-----|----------|------|---------|
| Gamma | `gamma-api.polymarket.com` | None | Event/market discovery |
| CLOB | `clob.polymarket.com` | EIP-712 (LIVE only) | Pricing + trading |

## Adding a New Strategy

1. Create `src/polymarket_trades/domain/strategies/your_strategy/detector.py` — implement `DetectorProtocol`
2. Create `src/polymarket_trades/domain/strategies/your_strategy/opportunity.py` — extend `Opportunity`
3. Register in `src/polymarket_trades/application/container.py`

Three files to add, zero files to modify.

## Deployment

Works with Dokku, Coolify, or any herokuish-compatible platform. The Python buildpack detects `uv.lock` and uses `uv` natively.

```bash
# Dokku
dokku apps:create polymarket-trades
dokku storage:ensure-directory polymarket-trades
dokku storage:mount polymarket-trades /var/lib/dokku/data/storage/polymarket-trades:/app/data
dokku config:set polymarket-trades TRADE_MODE=PAPER TOTAL_CAPITAL=1000
git push dokku main
```

Set `DATA_DIR` to control where the SQLite database is stored (default: `data/`). Mount a persistent volume at that path so data survives restarts.
