from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, order=True)
class Price:
    """Price in range [0.0, 1.0]. Uses Decimal for financial precision."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError(f"Price requires Decimal, got {type(self.value).__name__}")
        if self.value < 0:
            raise ValueError("Price must be non-negative")
        if self.value > 1:
            raise ValueError("Price cannot exceed 1.0")

    def __sub__(self, other: Price) -> Decimal:
        return self.value - other.value

    def __add__(self, other: Price) -> Decimal:
        return self.value + other.value
