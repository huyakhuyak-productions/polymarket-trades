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
