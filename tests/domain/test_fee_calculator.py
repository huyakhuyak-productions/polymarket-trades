from decimal import Decimal
import pytest
from polymarket_trades.domain.services.fee_calculator import FeeCalculator, MarketCategory
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.price import Price

class TestFeeCalculator:
    def setup_method(self):
        self.calc = FeeCalculator(crypto_fee_rate=Decimal("0.25"), sports_fee_rate=Decimal("0.0175"))

    def test_fee_exempt_market_returns_zero(self):
        fee = self.calc.estimate(price=Price(Decimal("0.50")), quantity=Decimal("100"), category=MarketCategory.FEE_EXEMPT, is_maker=False)
        assert fee == Money(Decimal("0"))

    def test_maker_fee_always_zero(self):
        fee = self.calc.estimate(price=Price(Decimal("0.50")), quantity=Decimal("100"), category=MarketCategory.CRYPTO, is_maker=True)
        assert fee == Money(Decimal("0"))

    def test_crypto_fee_at_midpoint(self):
        fee = self.calc.estimate(price=Price(Decimal("0.50")), quantity=Decimal("100"), category=MarketCategory.CRYPTO, is_maker=False)
        # fee = 100 * 0.50 * 0.25 * (0.50 * 0.50)^2 = 100 * 0.0078125 = 0.78125
        assert fee == Money(Decimal("0.781250"))

    def test_crypto_fee_near_certain(self):
        fee = self.calc.estimate(price=Price(Decimal("0.95")), quantity=Decimal("100"), category=MarketCategory.CRYPTO, is_maker=False)
        assert fee.value < Decimal("0.06")

    def test_sports_fee_at_midpoint(self):
        fee = self.calc.estimate(price=Price(Decimal("0.50")), quantity=Decimal("100"), category=MarketCategory.SPORTS, is_maker=False)
        # fee = 100 * 0.50 * 0.0175 * (0.25)^1 = 0.21875
        assert fee == Money(Decimal("0.218750"))

    def test_category_from_string_crypto(self):
        assert MarketCategory.from_string("crypto") == MarketCategory.CRYPTO
        assert MarketCategory.from_string("Crypto") == MarketCategory.CRYPTO

    def test_category_from_string_sports(self):
        assert MarketCategory.from_string("ncaab") == MarketCategory.SPORTS
        assert MarketCategory.from_string("Serie A") == MarketCategory.SPORTS

    def test_category_from_string_unknown_is_fee_exempt(self):
        assert MarketCategory.from_string("politics") == MarketCategory.FEE_EXEMPT
        assert MarketCategory.from_string("") == MarketCategory.FEE_EXEMPT

    def test_zero_quantity_returns_zero_fee(self):
        fee = self.calc.estimate(price=Price(Decimal("0.50")), quantity=Decimal("0"), category=MarketCategory.CRYPTO, is_maker=False)
        assert fee == Money(Decimal("0"))
