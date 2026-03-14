from __future__ import annotations
from decimal import Decimal
from enum import Enum
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.price import Price

class MarketCategory(str, Enum):
    FEE_EXEMPT = "FEE_EXEMPT"
    CRYPTO = "CRYPTO"
    SPORTS = "SPORTS"

    @classmethod
    def from_string(cls, category: str) -> MarketCategory:
        lower = category.lower().strip()
        if lower in ("crypto", "cryptocurrency"):
            return cls.CRYPTO
        if lower in ("ncaab", "serie a", "serie_a", "sports"):
            return cls.SPORTS
        return cls.FEE_EXEMPT

_EXPONENT = {MarketCategory.CRYPTO: 2, MarketCategory.SPORTS: 1}

class FeeCalculator:
    """fee = C * p * feeRate * (p * (1 - p))^exponent"""
    def __init__(self, crypto_fee_rate: Decimal = Decimal("0.25"), sports_fee_rate: Decimal = Decimal("0.0175")) -> None:
        self._rates = {MarketCategory.CRYPTO: crypto_fee_rate, MarketCategory.SPORTS: sports_fee_rate}

    def estimate(self, price: Price, quantity: Decimal, category: MarketCategory, is_maker: bool) -> Money:
        if is_maker or category == MarketCategory.FEE_EXEMPT or quantity == 0:
            return Money(Decimal("0"))
        p = price.value
        fee_rate = self._rates[category]
        exponent = _EXPONENT[category]
        variance = p * (Decimal("1") - p)
        fee = quantity * p * fee_rate * (variance ** exponent)
        return Money(fee)
