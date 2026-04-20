import json
import logging
import sqlite3
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Dict, List, Optional

from models import Trade, MonologueEntry, ScholarInsight

log = logging.getLogger(__name__)

class CustomEncoder(json.JSONEncoder):
    """Safely encodes Dataclasses, Enums, and Datetimes for JSON IPC."""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)

class Database:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_tables(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY, 
                    timestamp_open TEXT NOT NULL, 
                    timestamp_close TEXT,
                    symbol TEXT NOT NULL, 
                    bias TEXT NOT NULL, 
                    entry_price REAL NOT NULL,
                    exit_price REAL, 
                    position_size_usd REAL NOT NULL, 
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL, 
                    status TEXT NOT NULL, 
                    pnl_usd REAL,
                    pnl_pct REAL, 
                    scout_reasoning TEXT, 
                    risk_reasoning TEXT, 
                    trailing_extreme_price REAL NOT NULL DEFAULT 0.0
                );
                CREATE TABLE IF NOT EXISTS monologue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    timestamp TEXT NOT NULL, 
                    agent TEXT NOT NULL, 
                    message TEXT NOT NULL, 
                    severity TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scholar_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    timestamp TEXT NOT NULL, 
                    period_start TEXT NOT NULL, 
                    period_end TEXT NOT NULL, 
                    total_trades INTEGER, 
                    win_rate REAL, 
                    total_pnl REAL, 
                    lessons TEXT, 
                    parameter_changes TEXT, 
                    market_regime TEXT, 
                    reasoning TEXT
                );
                CREATE TABLE IF NOT EXISTS pivot_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    timestamp TEXT NOT NULL, 
                    old_bias TEXT NOT NULL, 
                    new_bias TEXT NOT NULL, 
                    trigger_price REAL, 
                    broken_level REAL, 
                    volume_ratio REAL, 
                    reasoning TEXT
                );
                CREATE TABLE IF NOT EXISTS dynamic_config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    timestamp TEXT NOT NULL, 
                    config_json TEXT NOT NULL, 
                    changed_by TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS q_table (
                    state_key TEXT PRIMARY KEY, 
                    action_values TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS system_flags (
                    key TEXT PRIMARY KEY, 
                    value TEXT NOT NULL
                );
            """)

    # ── V3 Safe JSON Multi-Process Memory Syncing ────────────
    def set_memory_state(self, key: str, obj):
        if obj is None:
            return
        try:
            json_str = json.dumps(obj, cls=CustomEncoder)
            b64 = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO system_flags (key, value) VALUES (?, ?)", 
                    (key, b64)
                )
        except Exception as e:
            log.error(f"Failed to serialize state {key}: {e}")

    def get_memory_state(self, key: str):
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM system_flags WHERE key = ?", (key,)).fetchone()
            if row:
                try:
                    decoded = base64.b64decode(row["value"]).decode('utf-8')
                    return json.loads(decoded)
                except Exception:
                    return None
            return None

    def set_system_flag(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO system_flags (key, value) VALUES (?, ?)", 
                (key, value)
            )

    def get_system_flag(self, key: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM system_flags WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    # ── Normal DB Operations ────────
    def insert_trade(self, trade: Trade):
        trailing_extreme = trade.trailing_extreme_price if trade.trailing_extreme_price != 0.0 else trade.entry_price
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    trade.id, 
                    trade.timestamp_open.isoformat(), 
                    trade.timestamp_close.isoformat() if trade.timestamp_close else None,
                    trade.symbol, 
                    trade.bias.value, 
                    trade.entry_price, 
                    trade.exit_price, 
                    trade.position_size_usd,
                    trade.stop_loss, 
                    trade.take_profit, 
                    trade.status.value, 
                    trade.pnl_usd, 
                    trade.pnl_pct,
                    trade.scout_reasoning, 
                    trade.risk_reasoning, 
                    trailing_extreme
                )
            )

    def update_trade(self, trade_id: str, **kwargs):
        if not kwargs:
            return
        set_parts =[f"{k} = ?" for k in kwargs.keys()]
        values = list(kwargs.values()) + [trade_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE trades SET {', '.join(set_parts)} WHERE id = ?", values)

    def get_trades(self, days_back: int = 30) -> List[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE timestamp_open > ? ORDER BY timestamp_open DESC", 
                (cutoff,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_open_trades(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY timestamp_open ASC").fetchall()
            return[dict(r) for r in rows]

    def get_pending_trades(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM trades WHERE status = 'PENDING' ORDER BY timestamp_open ASC").fetchall()
            return[dict(r) for r in rows]

    def get_active_trades(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM trades WHERE status IN ('OPEN', 'PENDING') ORDER BY timestamp_open ASC").fetchall()
            return[dict(r) for r in rows]

    def get_trade_stats(self, days_back: int = 7) -> Dict:
        trades = self.get_trades(days_back)
        closed =[t for t in trades if t["status"] == "CLOSED"]
        wins =[t for t in closed if (t.get("pnl_usd") or 0) > 0]
        total_pnl = sum(t.get("pnl_usd") or 0 for t in closed)
        return {
            "total": len(closed), 
            "wins": len(wins), 
            "losses": len(closed) - len(wins),
            "win_rate": len(wins) / max(len(closed), 1), 
            "total_pnl": total_pnl, 
            "avg_rr": 0
        }

    def add_monologue(self, entry: MonologueEntry):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO monologue (timestamp, agent, message, severity) VALUES (?,?,?,?)",
                (entry.timestamp.isoformat(), entry.agent, entry.message, entry.severity)
            )

    def get_monologue(self, limit: int = 50) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM monologue ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return[dict(r) for r in reversed(rows)]

    def add_scholar_review(self, insight: ScholarInsight):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO scholar_reviews 
                (timestamp, period_start, period_end, total_trades, win_rate, total_pnl, 
                lessons, parameter_changes, market_regime, reasoning) 
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    insight.timestamp.isoformat(), 
                    insight.period_start.isoformat(), 
                    insight.period_end.isoformat(),
                    insight.total_trades, 
                    insight.win_rate, 
                    insight.total_pnl, 
                    json.dumps(insight.lessons),
                    json.dumps(insight.parameter_changes), 
                    insight.market_regime, 
                    insight.reasoning
                )
            )

    def get_scholar_reviews(self, limit: int = 10) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM scholar_reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def add_pivot_event(self, event: dict):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO pivot_events 
                (timestamp, old_bias, new_bias, trigger_price, broken_level, volume_ratio, reasoning) 
                VALUES (?,?,?,?,?,?,?)""",
                (
                    event["timestamp"], event["old_bias"], event["new_bias"], 
                    event["trigger_price"], event["broken_level"], 
                    event["volume_ratio"], event["reasoning"]
                )
            )

    def get_q_values(self, state_key: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT action_values FROM q_table WHERE state_key = ?", (state_key,)).fetchone()
            if row:
                return json.loads(row["action_values"])
            return None

    def upsert_q_values(self, state_key: str, action_values: Dict):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO q_table (state_key, action_values) VALUES (?, ?) 
                ON CONFLICT(state_key) DO UPDATE SET action_values = excluded.action_values""",
                (state_key, json.dumps(action_values))
            )

    def save_config_snapshot(self, config_dict: Dict, changed_by: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO dynamic_config_history (timestamp, config_json, changed_by) VALUES (?,?,?)",
                (datetime.now(timezone.utc).isoformat(), json.dumps(config_dict), changed_by)
            )

    def get_latest_config_snapshot(self) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT config_json FROM dynamic_config_history ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                return json.loads(row["config_json"])
            return None

    def reset_trades_only(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM trades")
            conn.execute("DELETE FROM pivot_events")

    def reset_all_data(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM trades")
            conn.execute("DELETE FROM monologue")
            conn.execute("DELETE FROM scholar_reviews")
            conn.execute("DELETE FROM pivot_events")
            conn.execute("DELETE FROM q_table")
            conn.execute("DELETE FROM dynamic_config_history")

    def vacuum(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            conn.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()
