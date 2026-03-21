from decimal import Decimal
from pydantic import Field
from pydantic_settings import BaseSettings
from polymarket_trades.domain.value_objects.trade_mode import TradeMode


class Settings(BaseSettings):
    model_config = {"env_prefix": ""}

    scan_interval_seconds: int = 300
    near_certain_threshold: Decimal = Decimal("0.95")
    min_profit_threshold: Decimal = Decimal("0.005")
    max_single_position_pct: Decimal = Decimal("0.025")
    max_total_exposure_pct: Decimal = Decimal("1.0")
    min_market_liquidity: Decimal = Decimal("100")
    min_minutes_to_close: int = 10
    order_timeout_seconds: int = 300
    total_capital: Decimal = Decimal("2000")
    trade_mode: TradeMode = TradeMode.PAPER
    polymarket_private_key: str = ""
    crypto_fee_rate: Decimal = Decimal("0.25")
    sports_fee_rate: Decimal = Decimal("0.0175")
    log_level: str = "INFO"
    gamma_base_url: str = "https://gamma-api.polymarket.com"
    clob_base_url: str = "https://clob.polymarket.com"
    gamma_page_size: int = 100
    rate_limit_requests_per_second: int = 10
    data_dir: str = "data"
