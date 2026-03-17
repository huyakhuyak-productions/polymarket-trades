from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from polymarket_trades.application.container import build_container, close_container
from polymarket_trades.application.scheduler import run_scheduler
from polymarket_trades.infrastructure.config.logging import configure_logging
from polymarket_trades.infrastructure.config.settings import Settings
from polymarket_trades.domain.value_objects.trade_mode import TradeMode

app = typer.Typer(name="polymarket-trades", help="Polymarket low-risk trading bot")
console = Console()


def _get_settings(dry_run: bool, log_level: str) -> Settings:
    mode = TradeMode.PAPER if dry_run else TradeMode.LIVE
    return Settings(trade_mode=mode, log_level=log_level)


@app.command()
def run(
    dry_run: bool = typer.Option(True, "--dry-run/--live", help="Paper or live mode"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
) -> None:
    """Run the trading bot in a continuous loop."""
    settings = _get_settings(dry_run, log_level)
    console.print(
        f"[bold]Starting bot in [cyan]{settings.trade_mode.value}[/cyan] mode...[/bold]"
    )
    asyncio.run(run_scheduler(settings=settings))


@app.command()
def scan(
    dry_run: bool = typer.Option(True, "--dry-run/--live", help="Paper or live mode"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
) -> None:
    """Run a single scan cycle and print results."""
    settings = _get_settings(dry_run, log_level)
    configure_logging(log_level=settings.log_level)

    async def _scan() -> None:
        container = await build_container(settings=settings)
        try:
            opportunities = await container.scan_opportunities.execute()
            if not opportunities:
                console.print("[yellow]No opportunities found.[/yellow]")
                return

            table = Table(title="Detected Opportunities")
            table.add_column("Strategy", style="cyan")
            table.add_column("Market ID")
            table.add_column("Event")
            table.add_column("Entry Price", justify="right")
            table.add_column("Expected Profit", justify="right", style="green")

            for opp in opportunities:
                table.add_row(
                    opp.strategy_type,
                    opp.market_id[:16] + "..." if len(opp.market_id) > 16 else opp.market_id,
                    opp.event_title[:40],
                    str(opp.entry_price),
                    str(opp.expected_profit.value),
                )
            console.print(table)
        finally:
            await close_container(container)

    asyncio.run(_scan())


@app.command()
def report(
    mode: str = typer.Option("all", "--mode", help="Filter by mode: paper, live, or all"),
    log_level: str = typer.Option("WARNING", "--log-level", help="Logging level"),
) -> None:
    """Show strategy performance report."""
    configure_logging(log_level=log_level)

    async def _report() -> None:
        container = await build_container(settings=Settings(log_level=log_level))
        try:
            trade_mode = None
            if mode.lower() == "paper":
                trade_mode = TradeMode.PAPER
            elif mode.lower() == "live":
                trade_mode = TradeMode.LIVE

            reports = await container.monitor_positions.execute(mode=trade_mode)
            if not reports:
                console.print("[yellow]No resolved positions to report.[/yellow]")
                return

            table = Table(title="Strategy Performance Report")
            table.add_column("Strategy", style="cyan")
            table.add_column("Trades", justify="right")
            table.add_column("Wins", justify="right")
            table.add_column("Win %", justify="right")
            table.add_column("Total P&L", justify="right", style="green")
            table.add_column("Avg Return", justify="right")

            for r in reports:
                pnl_style = "green" if r.total_pnl >= 0 else "red"
                table.add_row(
                    r.strategy,
                    str(r.trades),
                    str(r.wins),
                    f"{r.win_pct:.1f}%",
                    f"[{pnl_style}]{r.total_pnl:.6f}[/{pnl_style}]",
                    f"{r.avg_return_pct:.6f}",
                )
            console.print(table)
        finally:
            await close_container(container)

    asyncio.run(_report())


@app.command()
def positions(
    mode: str = typer.Option("all", "--mode", help="Filter by mode: paper, live, or all"),
    log_level: str = typer.Option("WARNING", "--log-level", help="Logging level"),
) -> None:
    """List all positions."""
    configure_logging(log_level=log_level)

    async def _positions() -> None:
        container = await build_container(settings=Settings(log_level=log_level))
        try:
            trade_mode = None
            if mode.lower() == "paper":
                trade_mode = TradeMode.PAPER
            elif mode.lower() == "live":
                trade_mode = TradeMode.LIVE

            all_positions = await container.position_tracker.get_all_positions(mode=trade_mode)
            if not all_positions:
                console.print("[yellow]No positions found.[/yellow]")
                return

            table = Table(title=f"Positions ({len(all_positions)} total)")
            table.add_column("ID", style="dim")
            table.add_column("Strategy", style="cyan")
            table.add_column("Market")
            table.add_column("Side")
            table.add_column("Entry", justify="right")
            table.add_column("Current", justify="right")
            table.add_column("Qty", justify="right")
            table.add_column("P&L", justify="right")
            table.add_column("Status")
            table.add_column("Mode")
            table.add_column("Link", style="blue")

            for pos in all_positions:
                pnl_str = ""
                if pos.pnl is not None:
                    pnl_style = "green" if pos.pnl >= 0 else "red"
                    pnl_str = f"[{pnl_style}]{pos.pnl:.4f}[/{pnl_style}]"

                link = (
                    f"https://polymarket.com/event/{pos.event_slug}"
                    if pos.event_slug
                    else ""
                )

                table.add_row(
                    str(pos.id)[:8],
                    pos.opportunity_type,
                    pos.market_id[:12] + "..." if len(pos.market_id) > 12 else pos.market_id,
                    pos.side.value,
                    str(pos.entry_price),
                    str(pos.current_price),
                    f"{pos.quantity:.2f}",
                    pnl_str,
                    pos.status.value,
                    pos.mode.value,
                    link,
                )
            console.print(table)
        finally:
            await close_container(container)

    asyncio.run(_positions())


@app.command(name="backfill-slugs")
def backfill_slugs(
    log_level: str = typer.Option("WARNING", "--log-level", help="Logging level"),
) -> None:
    """Backfill event_slug for positions that are missing it (one-time migration)."""
    configure_logging(log_level=log_level)

    async def _backfill() -> None:
        container = await build_container(settings=Settings(log_level=log_level))
        try:
            gamma = container._gamma_client
            if gamma is None:
                console.print("[red]Gamma client not available.[/red]")
                return

            all_positions = await container.position_tracker.get_all_positions()
            missing = [p for p in all_positions if not p.event_slug]
            if not missing:
                console.print("[green]All positions already have event slugs.[/green]")
                return

            console.print(f"Found {len(missing)} positions missing event_slug.")

            # Group by (strategy, market_id) to minimize API calls
            seen: dict[str, str] = {}
            updated = 0
            errors = 0

            for pos in missing:
                if pos.market_id in seen:
                    slug = seen[pos.market_id]
                else:
                    try:
                        if pos.opportunity_type == "neg_risk_discount":
                            event = await gamma.fetch_event_by_id(pos.market_id)
                            slug = event.slug
                        else:
                            slug = await gamma.fetch_event_slug_for_market(pos.market_id)
                        seen[pos.market_id] = slug
                    except Exception as exc:
                        console.print(
                            f"[yellow]Failed to fetch slug for {pos.market_id}: {exc}[/yellow]"
                        )
                        errors += 1
                        continue

                if slug:
                    await container.position_tracker.update_event_slug(
                        str(pos.id), slug
                    )
                    updated += 1
                    console.print(
                        f"  [green]Updated[/green] {str(pos.id)[:8]} → {slug}"
                    )
                else:
                    console.print(
                        f"  [yellow]No slug found for {str(pos.id)[:8]} (market_id={pos.market_id})[/yellow]"
                    )

            console.print(
                f"\n[bold]Done:[/bold] {updated} updated, {errors} errors, "
                f"{len(missing) - updated - errors} no slug found."
            )
        finally:
            await close_container(container)

    asyncio.run(_backfill())
