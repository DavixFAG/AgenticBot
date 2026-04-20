import json
import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np

from config import BOT_CONFIG
from database import Database
from models import MonologueEntry, ScholarInsight

log = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.model = None
        self.available = False
        self._init()

    def _init(self):
        key = BOT_CONFIG.ai.gemini_api_key
        if not key:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            
            self.model = genai.GenerativeModel(
                model_name=BOT_CONFIG.ai.gemini_model,
                generation_config=genai.types.GenerationConfig(
                    temperature=BOT_CONFIG.ai.gemini_temperature, 
                    max_output_tokens=BOT_CONFIG.ai.gemini_max_tokens, 
                    response_mime_type="application/json"
                ),
                system_instruction="You are the Scholar agent of a BTC/USD trading bot. Always respond in valid JSON."
            )
            self.available = True
        except Exception as e:
            log.error("[Scholar] Gemini init failed: %s", e)

    def generate(self, prompt: str, retries: int = 3) -> Optional[str]:
        if not self.available:
            return None
            
        for attempt in range(retries):
            try:
                resp = self.model.generate_content(prompt)
                return getattr(resp, "text", None) or "".join(getattr(p, "text", "") for p in resp.parts).strip()
            except Exception as e:
                if "429" in str(e):
                    time.sleep((attempt + 1) * 15)
                else:
                    log.error("[Scholar] Gemini error: %s", e)
                    return None
        return None

    def parse_json(self, text: str) -> Optional[Dict]:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        for pat in [r"```json\s*([\s\S]*?)\s*```", r"(\{[\s\S]*\})"]:
            m = re.search(pat, text)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    continue
        return None

class QLearningEngine:
    ACTIONS =[
        "widen_bb", "tighten_bb", "speed_macd", "slow_macd", 
        "widen_sl", "tighten_sl", "raise_confidence", "lower_confidence", 
        "early_entry", "late_entry", "hold_params"
    ]

    def __init__(self, db: Database):
        self.db = db
        self.lr = BOT_CONFIG.dynamic.learning_rate
        self.gamma = BOT_CONFIG.dynamic.discount_factor
        self.epsilon = BOT_CONFIG.dynamic.exploration_rate

    def discretize_state(self, volatility: float, trend_strength: float, win_rate: float) -> str:
        v = "high" if volatility > 0.015 else "medium" if volatility > 0.008 else "low"
        t = "trending" if trend_strength > 0.6 else "ranging"
        w = "high" if win_rate > 0.6 else "medium" if win_rate > 0.4 else "low"
        return f"{v}_{t}_{w}"

    def get_q(self, state: str) -> Dict[str, float]:
        q = self.db.get_q_values(state)
        if not q:
            q = {a: 0.0 for a in self.ACTIONS}
            self.db.upsert_q_values(state, q)
        return q

    def choose(self, state: str) -> str:
        if random.random() < self.epsilon:
            return random.choice(self.ACTIONS)
        q = self.get_q(state)
        return max(q, key=q.get)

    def update(self, state: str, action: str, reward: float, next_state: str):
        q = self.get_q(state)
        q_next = self.get_q(next_state)
        q[action] = round(q[action] + self.lr * (reward + self.gamma * max(q_next.values()) - q[action]), 6)
        self.db.upsert_q_values(state, q)

    def apply(self, action: str) -> Dict:
        d = BOT_CONFIG.dynamic
        changes = {}
        
        def _change(p, o, n):
            if o != n:
                setattr(d, p, n)
                changes[p] = {"old": o, "new": n}
        
        if action == "widen_bb":
            _change("bb_std", d.bb_std, min(3.0, round(d.bb_std + 0.2, 1)))
        elif action == "tighten_bb":
            _change("bb_std", d.bb_std, max(1.5, round(d.bb_std - 0.2, 1)))
        elif action == "widen_sl":
            _change("sl_max_pct", d.sl_max_pct, min(3.0, round(d.sl_max_pct + 0.25, 2)))
        elif action == "tighten_sl":
            _change("sl_max_pct", d.sl_max_pct, max(0.5, round(d.sl_max_pct - 0.25, 2)))
        elif action == "raise_confidence":
            _change("min_confidence", d.min_confidence, min(0.80, round(d.min_confidence + 0.05, 2)))
        elif action == "lower_confidence":
            _change("min_confidence", d.min_confidence, max(0.35, round(d.min_confidence - 0.05, 2)))
        elif action == "early_entry":
            _change("execution_window_start", d.execution_window_start, max(52, d.execution_window_start - 1))
        elif action == "late_entry":
            _change("execution_window_start", d.execution_window_start, min(58, d.execution_window_start + 1))
            
        return changes

class Scholar:
    def __init__(self, db: Database):
        self.db = db
        self.rl = QLearningEngine(db)
        self.gemini = GeminiClient()

    def should_review(self) -> bool:
        recent = self.db.get_trades(days_back=30)
        closed =[t for t in recent if t["status"] == "CLOSED"]
        
        reviews = self.db.get_scholar_reviews(limit=1)
        
        # If there are no previous reviews, trigger when we hit the batch size
        if not reviews:
            return len(closed) >= BOT_CONFIG.dynamic.scholar_trigger_trades
            
        # Get the exact time the last review happened
        last_review_str = reviews[0].get("timestamp", "")
        if not last_review_str:
            return len(closed) >= BOT_CONFIG.dynamic.scholar_trigger_trades
            
        last_review_time = datetime.fromisoformat(last_review_str)
        if last_review_time.tzinfo is None:
            last_review_time = last_review_time.replace(tzinfo=timezone.utc)
            
        # Count how many trades closed AFTER the last review
        new_closed_trades = 0
        for t in closed:
            close_str = t.get("timestamp_close")
            if close_str:
                close_time = datetime.fromisoformat(close_str)
                if close_time.tzinfo is None:
                    close_time = close_time.replace(tzinfo=timezone.utc)
                    
                if close_time > last_review_time:
                    new_closed_trades += 1
                    
        return new_closed_trades >= BOT_CONFIG.dynamic.scholar_trigger_trades

    def meta_strategy_update(self, volatility: float, trend_strength: float) -> ScholarInsight:
        now = datetime.now(timezone.utc)
        n = BOT_CONFIG.dynamic.scholar_trigger_trades
        
        closed =[t for t in self.db.get_trades(days_back=30) if t["status"] == "CLOSED"]
        last_n = closed[:n]
        
        if not last_n:
            return self._empty_insight(now)

        wins =[t for t in last_n if (t.get("pnl_usd") or 0) > 0]
        losses =[t for t in last_n if (t.get("pnl_usd") or 0) <= 0]
        total_pnl = sum(t.get("pnl_usd") or 0 for t in last_n)
        win_rate = len(wins) / len(last_n) if last_n else 0.0

        lessons =[]
        analysis = "Gemini unavailable"
        
        if self.gemini.available:
            analysis, lessons = self._gemini_meta_review(last_n, volatility, trend_strength)
        else:
            lessons = self._rule_based_review(last_n, volatility, win_rate)

        state = self.rl.discretize_state(volatility, trend_strength, win_rate)
        avg_pnl = total_pnl / len(last_n) if last_n else 0
        reward = (win_rate - 0.5) * 2 + np.clip(avg_pnl / 100, -0.5, 0.5) 
        
        action = self.rl.choose(state)
        changes = self.rl.apply(action)
        self.rl.update(state, action, float(reward), state)

        if changes:
            self.db.save_config_snapshot(vars(BOT_CONFIG.dynamic).copy(), changed_by="scholar")

        regime = "volatile" if volatility > 0.015 else "trending" if trend_strength > 0.6 else "ranging"
        
        insight = ScholarInsight(
            timestamp=now,
            period_start=now - timedelta(days=1),
            period_end=now,
            total_trades=len(last_n),
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_risk_reward=0,
            lessons=lessons,
            parameter_changes=changes,
            market_regime=regime,
            reasoning=analysis
        )
        
        self.db.add_scholar_review(insight)
        
        self.db.add_monologue(MonologueEntry(
            timestamp=now, agent="Scholar", 
            message=f"META-UPDATE: {len(last_n)} trades | {len(wins)}W {len(losses)}L | ${total_pnl:,.2f}", 
            severity="action"
        ))
        
        for l in lessons:
            self.db.add_monologue(MonologueEntry(timestamp=now, agent="Scholar", message=l, severity="info"))
            
        return insight

    def _gemini_meta_review(self, trades, volatility, trend_strength):
        prompt = f"""Analyze {len(trades)} trades. Volatility: {volatility}, Trend: {trend_strength}.
        Trades: {json.dumps([{'bias': t['bias'], 'pnl': t.get('pnl_usd')} for t in trades])}
        Return JSON: {{"analysis": "", "lessons": ["l1", "l2"], "recommended_min_confidence": {BOT_CONFIG.dynamic.min_confidence}}}"""
        
        raw = self.gemini.generate(prompt)
        
        if not raw:
            return "Gemini unavailable", self._rule_based_review(trades, volatility, 0)
            
        parsed = self.gemini.parse_json(raw)
        if parsed:
            lessons = parsed.get("lessons",[])
            new_conf = parsed.get("recommended_min_confidence")
            if isinstance(new_conf, (int, float)):
                new_conf = float(np.clip(new_conf, 0.35, 0.80))
                if abs(new_conf - BOT_CONFIG.dynamic.min_confidence) > 0.01:
                    BOT_CONFIG.dynamic.min_confidence = round(new_conf, 2)
                    lessons.append(f"Adjusted min_confidence to {new_conf}")
            return parsed.get("analysis", ""), lessons
            
        return raw[:200],[]

    def _rule_based_review(self, trades, volatility, win_rate):
        lessons =[]
        if win_rate < 0.4:
            lessons.append("Low win rate. Raising confidence threshold.")
        if volatility > 0.015:
            lessons.append("High vol. Widening SL to avoid noise stops.")
        return lessons

    def _empty_insight(self, now):
        return ScholarInsight(
            timestamp=now, period_start=now, period_end=now, total_trades=0, 
            win_rate=0, total_pnl=0, avg_risk_reward=0, lessons=["No trades"], 
            parameter_changes={}, market_regime="unknown", reasoning="No trades"
        )
