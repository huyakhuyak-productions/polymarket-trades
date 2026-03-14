from enum import Enum


class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class PositionStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    ENTERED = "ENTERED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    PNL_CALCULATED = "P&L_CALCULATED"


class TimeInForce(str, Enum):
    GTC = "GTC"
    GTD = "GTD"
    FOK = "FOK"
    FAK = "FAK"
