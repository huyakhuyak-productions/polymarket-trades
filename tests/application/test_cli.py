from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from polymarket_trades.application.cli import app
from polymarket_trades.domain.value_objects.trade_mode import TradeMode

runner = CliRunner()


def _make_mock_container():
    container = MagicMock()
    container.scan_opportunities = AsyncMock()
    container.monitor_positions = AsyncMock()
    container.position_tracker = AsyncMock()
    container.db = AsyncMock()
    container._gamma_client = None
    container.settings = MagicMock()
    container.settings.trade_mode = TradeMode.PAPER
    container.settings.log_level = "WARNING"
    return container


class TestCli:
    def test_scan_no_opportunities(self):
        mock_container = _make_mock_container()
        mock_container.scan_opportunities.execute.return_value = []

        with (
            patch(
                "polymarket_trades.application.cli.build_container",
                return_value=mock_container,
            ),
            patch(
                "polymarket_trades.application.cli.close_container",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["scan"])
            assert result.exit_code == 0
            assert "No opportunities found" in result.output

    def test_report_no_positions(self):
        mock_container = _make_mock_container()
        mock_container.monitor_positions.execute.return_value = []

        with (
            patch(
                "polymarket_trades.application.cli.build_container",
                return_value=mock_container,
            ),
            patch(
                "polymarket_trades.application.cli.close_container",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["report"])
            assert result.exit_code == 0
            assert "No resolved positions" in result.output

    def test_positions_no_positions(self):
        mock_container = _make_mock_container()
        mock_container.position_tracker.get_all_positions.return_value = []

        with (
            patch(
                "polymarket_trades.application.cli.build_container",
                return_value=mock_container,
            ),
            patch(
                "polymarket_trades.application.cli.close_container",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["positions"])
            assert result.exit_code == 0
            assert "No positions found" in result.output

    def test_scan_default_is_dry_run(self):
        mock_container = _make_mock_container()
        mock_container.scan_opportunities.execute.return_value = []

        with (
            patch(
                "polymarket_trades.application.cli.build_container",
                return_value=mock_container,
            ) as mock_build,
            patch(
                "polymarket_trades.application.cli.close_container",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["scan"])
            assert result.exit_code == 0
            settings = mock_build.call_args[1]["settings"]
            assert settings.trade_mode == TradeMode.PAPER
