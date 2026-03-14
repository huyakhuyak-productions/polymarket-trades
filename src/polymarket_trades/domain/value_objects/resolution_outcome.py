from enum import Enum


class ResolutionOutcome(str, Enum):
    """How a market resolved."""

    YES = "YES"
    NO = "NO"
    INVALID = "INVALID"
