"""
models.py — Properly formatted Dataclasses.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

class Bias(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class SignalStrength(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"

class TradeStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

@dataclass
class IndicatorSnapshot:
    timestamp: datetime
    price: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_pct_b: float
    ma20: float
    ma50: float
    atr: float
    volume_current: float
    volume_avg: float
    volume_ratio: float

@dataclass
class WickRejection:
    timestamp: datetime
    direction: str
    price: float
    wick_length: float
    body_length: float
    wick_ratio: float
    wick_pct_of_range: float
    rejected_level: float
    level_type: str
    candle_low: float = 0.0
    candle_high: float = 0.0

@dataclass
class SupportResistance:
    level: float
    strength: int
    level_type: str
    last_tested: datetime

@dataclass
class ScoutSignal:
    timestamp: datetime
    bias: Bias
    strength: SignalStrength
    confidence: float
    entry_price: float
    sniper_entry_price: float
    indicators: IndicatorSnapshot
    nearest_support: float
    nearest_resistance: float
    wick_rejection: Optional[WickRejection]
    patterns_detected: List[str]
    reasoning: str
    confidence_breakdown: Dict[str, float]
    suggested_sl: float
    suggested_tp: float

@dataclass
class RiskVerdict:
    approved: bool
    original_signal: ScoutSignal
    position_size_usd: float
    position_size_pct: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    sl_distance_pct: float
    reasoning: str
    discipline_rules: Dict[str, str]
    warnings: List[str]

@dataclass
class Trade:
    id: str
    timestamp_open: datetime
    timestamp_close: Optional[datetime]
    symbol: str
    bias: Bias
    entry_price: float
    exit_price: Optional[float]
    position_size_usd: float
    stop_loss: float
    take_profit: float
    status: TradeStatus
    pnl_usd: Optional[float]
    pnl_pct: Optional[float]
    scout_reasoning: str
    risk_reasoning: str
    trailing_extreme_price: float = 0.0

@dataclass
class MetaStrategyUpdate:
    timestamp: datetime
    trades_reviewed: int
    wins: int
    losses: int
    total_pnl: float
    analysis: str
    lessons: List[str]
    parameter_changes: Dict[str, Dict]
    new_min_confidence: float
    market_assessment: str

@dataclass
class ScholarInsight:
    timestamp: datetime
    period_start: datetime
    period_end: datetime
    total_trades: int
    win_rate: float
    total_pnl: float
    avg_risk_reward: float
    lessons: List[str]
    parameter_changes: Dict[str, Dict]
    market_regime: str
    reasoning: str

@dataclass
class PivotEvent:
    timestamp: datetime
    old_bias: Bias
    new_bias: Bias
    trigger_price: float
    broken_level: float
    volume_ratio: float
    reasoning: str

@dataclass
class MonologueEntry:
    timestamp: datetime
    agent: str
    message: str
    severity: str
