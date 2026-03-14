from __future__ import annotations
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_USDC_PRECISION = Decimal("0.000001")


@dataclass(frozen=True, order=True)
class Money:
    """USDC amount with 6-decimal precision."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError(f"Money requires Decimal, got {type(self.value).__name__}")
        quantized = self.value.quantize(_USDC_PRECISION, rounding=ROUND_HALF_UP)
        if quantized < 0:
            raise ValueError("Money must be non-negative")
        object.__setattr__(self, "value", quantized)

    def __add__(self, other: Money) -> Money:
        return Money(self.value + other.value)

    def __sub__(self, other: Money) -> Decimal:
        """Returns Decimal (not Money) since result may be negative (e.g. P&L losses)."""
        return (self.value - other.value).quantize(_USDC_PRECISION, rounding=ROUND_HALF_UP)
