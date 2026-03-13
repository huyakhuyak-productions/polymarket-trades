---
alwaysApply: true
---

# Polymarket Trading Bot

## Architecture
Clean Architecture + DDD + TDD. Three layers:
- `domain/` — entities, value objects, ports (ABCs), services, strategies. Zero external imports.
- `application/` — use cases, scheduler, CLI, DI container. Depends on domain only.
- `infrastructure/` — adapters implementing ports, API clients, persistence. Depends on domain ports.

## Key Rules
- Domain layer must NEVER import from infrastructure or application
- All financial values use `Decimal`, never `float`
- All timestamps are UTC
- Paper mode (`--dry-run`) is the default. Live mode requires explicit `--live` flag.
- TDD: write failing tests first, then implement

## Running
- Tests: `pytest`
- Bot (paper): `python -m polymarket_trades run --dry-run`
- Bot (live): `python -m polymarket_trades run --live`
- Report: `python -m polymarket_trades report`

## Package Manager
Python with pip. No lockfile yet — use `pip install --editable ".[dev]"`.

## APIs
- Gamma API (`gamma-api.polymarket.com`) — event/market discovery, no auth
- CLOB API (`clob.polymarket.com`) — pricing (no auth) + trading (EIP-712 signing via py-clob-client)
