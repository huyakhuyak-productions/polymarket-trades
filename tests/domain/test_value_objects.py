from decimal import Decimal
import pytest
from polymarket_trades.domain.value_objects.price import Price

class TestPrice:
    def test_create_valid_price(self):
        p = Price(Decimal("0.50"))
        assert p.value == Decimal("0.50")

    def test_create_zero_price(self):
        p = Price(Decimal("0"))
        assert p.value == Decimal("0")

    def test_create_one_price(self):
        p = Price(Decimal("1"))
        assert p.value == Decimal("1")

    def test_reject_negative_price(self):
        with pytest.raises(ValueError, match="non-negative"):
            Price(Decimal("-0.01"))

    def test_reject_price_above_one(self):
        with pytest.raises(ValueError, match="cannot exceed 1"):
            Price(Decimal("1.01"))

    def test_price_equality(self):
        assert Price(Decimal("0.95")) == Price(Decimal("0.95"))

    def test_price_comparison(self):
        assert Price(Decimal("0.95")) > Price(Decimal("0.50"))

    def test_price_subtraction(self):
        result = Price(Decimal("1.0")) - Price(Decimal("0.95"))
        assert result == Decimal("0.05")

    def test_price_addition_capped(self):
        result = Price(Decimal("0.60")) + Price(Decimal("0.50"))
        assert result == Decimal("1.10")

    def test_price_from_float_rejected(self):
        with pytest.raises(TypeError):
            Price(0.5)


from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.outcome import Outcome, Side
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.domain.value_objects.trade_mode import TradeMode, PositionStatus, TimeInForce


class TestMoney:
    def test_create_valid_money(self):
        m = Money(Decimal("100.500000"))
        assert m.value == Decimal("100.500000")

    def test_reject_negative_money(self):
        with pytest.raises(ValueError, match="non-negative"):
            Money(Decimal("-1"))

    def test_money_quantizes_to_6_decimals(self):
        m = Money(Decimal("1.1234567890"))
        assert m.value == Decimal("1.123457")

    def test_money_addition(self):
        result = Money(Decimal("10")) + Money(Decimal("20.50"))
        assert result == Money(Decimal("30.50"))

    def test_money_subtraction_returns_decimal(self):
        result = Money(Decimal("30")) - Money(Decimal("10.25"))
        assert result == Decimal("19.750000")

    def test_money_subtraction_negative_result(self):
        result = Money(Decimal("10")) - Money(Decimal("30"))
        assert result == Decimal("-20.000000")

    def test_money_from_float_rejected(self):
        with pytest.raises(TypeError):
            Money(0.5)


class TestTokenId:
    def test_create_valid_token_id(self):
        t = TokenId("0xabc123def456")
        assert t.value == "0xabc123def456"

    def test_reject_empty_token_id(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            TokenId("")

    def test_reject_whitespace_token_id(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            TokenId("   ")

    def test_token_id_equality(self):
        assert TokenId("0xabc") == TokenId("0xabc")


class TestOutcome:
    def test_create_outcome(self):
        o = Outcome(side=Side.YES, price=Price(Decimal("0.75")))
        assert o.side == Side.YES
        assert o.price.value == Decimal("0.75")

    def test_side_values(self):
        assert Side.YES.value == "YES"
        assert Side.NO.value == "NO"


class TestEnums:
    def test_resolution_outcome_values(self):
        assert ResolutionOutcome.YES.value == "YES"
        assert ResolutionOutcome.NO.value == "NO"
        assert ResolutionOutcome.INVALID.value == "INVALID"

    def test_trade_mode_values(self):
        assert TradeMode.PAPER.value == "PAPER"
        assert TradeMode.LIVE.value == "LIVE"

    def test_position_status_values(self):
        statuses = [s.value for s in PositionStatus]
        assert "IDENTIFIED" in statuses
        assert "ENTERED" in statuses
        assert "MONITORING" in statuses
        assert "RESOLVED" in statuses
        assert "P&L_CALCULATED" in statuses

    def test_time_in_force_values(self):
        assert TimeInForce.GTC.value == "GTC"
        assert TimeInForce.GTD.value == "GTD"
        assert TimeInForce.FOK.value == "FOK"
        assert TimeInForce.FAK.value == "FAK"
