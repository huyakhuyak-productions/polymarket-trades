from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenId:
    """CLOB token identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("TokenId cannot be empty")
