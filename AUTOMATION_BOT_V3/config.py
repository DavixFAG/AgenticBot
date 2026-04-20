"""
config.py — V3.1 (Institutional Sniper Architecture)
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ExchangeConfig:
    exchange_id: str = "binance"
    symbol: str = os.getenv("EXCHANGE_SYMBOL", "BTC/USDT")
    api_key: str = os.getenv("EXCHANGE_API_KEY", "")
    api_secret: str = os.getenv("EXCHANGE_API_SECRET", "")
    sandbox: bool = os.getenv("EXCHANGE_SANDBOX", "true").lower() == "true"

@dataclass
class TimeframeConfig:
    primary: str = "1h"
    context: str = "4h"

@dataclass
class AIConfig:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    gemini_max_tokens: int = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

@dataclass
class DynamicConfig:
    # V3: Real-World Friction
    maker_fee_pct: float = 0.02
    taker_fee_pct: float = 0.05
    slippage_pct: float = 0.05

    # V3: Dynamic Execution Window
    execution_window_start: int = 57
    execution_window_end: int = 59

    # Strategy Parameters
    max_risk_per_trade_pct: float = 1.5
    max_open_positions: int = 2
    max_daily_loss_pct: float = 4.0
    max_drawdown_pct: float = 10.0
    max_position_size_usd: float = float(os.getenv("MAX_POSITION_SIZE_USD", "1000"))

    min_wick_ratio: float = 2.0
    min_wick_pct_of_range: float = 0.60
    wick_proximity_pct: float = 0.5

    bb_length: int = 20
    bb_std: float = 2.0
    bb_touch_threshold: float = 0.05
    bb_upper_threshold: float = 0.95

    rsi_length: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    ma_fast: int = 20
    ma_slow: int = 50

    sl_method: str = "wick"
    sl_wick_buffer_pct: float = 0.15
    sl_atr_multiplier: float = 1.0
    sl_max_pct: float = 1.5

    tp_rr_ratio: float = 2.5
    trailing_stop_pct: float = 0.5

    min_confidence: float = 0.55
    entry_cooldown_bars: int = 2

    pivot_lookback: int = 10
    pivot_cluster_pct: float = 0.5
    volume_breakout_multiplier: float = 1.5

    learning_rate: float = 0.1
    discount_factor: float = 0.95
    exploration_rate: float = 0.15

    scholar_trigger_trades: int = 5

@dataclass
class BotConfig:
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    timeframes: TimeframeConfig = field(default_factory=TimeframeConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    dynamic: DynamicConfig = field(default_factory=DynamicConfig)
    db_path: str = os.getenv("BOT_DB_PATH", "trading_bot.db")
    log_max_entries: int = 500

BOT_CONFIG = BotConfig()
