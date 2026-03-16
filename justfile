default:
    @just --list

# Run tests
test *args:
    uv run pytest {{args}}

# Run tests with verbose output
test-v *args:
    uv run pytest --verbose {{args}}

# Run the bot in paper mode (default)
run:
    uv run python -m polymarket_trades run --dry-run

# Run the bot in live mode
run-live:
    uv run python -m polymarket_trades run --live

# One-shot scan for opportunities
scan:
    uv run python -m polymarket_trades scan --dry-run

# Show performance report
report:
    uv run python -m polymarket_trades report

# Show open positions
positions:
    uv run python -m polymarket_trades positions

# Sync dependencies
sync:
    uv sync

# Lint
lint:
    uv run ruff check src/ tests/

# Format
fmt:
    uv run ruff format src/ tests/

# Lint + format
check: lint fmt

# Deploy to Dokku
deploy remote="dokku":
    git push {{remote}} feature/trading-bot:main
