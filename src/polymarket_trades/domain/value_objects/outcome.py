from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from polymarket_trades.domain.value_objects.price import Price


class Side(str, Enum):
    YES = "YES"
    NO = "NO"


@dataclass(frozen=True)
class Outcome:
    """A tradeable outcome with a side and price."""

    side: Side
    price: Price
