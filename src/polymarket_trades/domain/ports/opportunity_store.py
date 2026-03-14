from __future__ import annotations
from abc import ABC, abstractmethod
from polymarket_trades.domain.strategies.opportunity import Opportunity

class OpportunityStorePort(ABC):
    @abstractmethod
    async def save(self, opportunity: Opportunity) -> None: ...
    @abstractmethod
    async def find_existing(self, strategy_type: str, market_id: str, token_id: str) -> Opportunity | None: ...
