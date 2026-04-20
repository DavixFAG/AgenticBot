"""
risk_manager.py — V3.1 Sniper Sizing Math
Sizes positions based on the 50% Wick Retracement limits, slippage, and fees.
"""

from datetime import datetime, timezone
from typing import Optional

from config import BOT_CONFIG
from database import Database
from models import Bias, MonologueEntry, RiskVerdict, ScoutSignal

class RiskManager:
    def __init__(self, db: Database, portfolio_value: float = 10_000):
        self.db = db
        self.portfolio_value = portfolio_value
        self.kill_switch_active = False
        self.manual_override: Optional[str] = None

    def evaluate(self, signal: ScoutSignal) -> RiskVerdict:
        dyn = BOT_CONFIG.dynamic
        warnings_list = []
        deny = []
        log =[]
        
        win_start = dyn.execution_window_start
        win_end = dyn.execution_window_end

        discipline = {
            "max_risk_per_trade": f"{dyn.max_risk_per_trade_pct}%",
            "max_daily_loss": f"{dyn.max_daily_loss_pct}%",
            "max_drawdown": f"{dyn.max_drawdown_pct}%",
            "max_positions": str(dyn.max_open_positions),
            "min_risk_reward": f"{dyn.tp_rr_ratio}:1 target",
            "min_confidence": f"{dyn.min_confidence:.0%}",
            "sl_method": dyn.sl_method,
            "sl_max": f"{dyn.sl_max_pct}%",
            "execution_window": f"Minutes {win_start} to {win_end}",
            "fees_included": "Yes (Maker/Taker/Slippage)",
        }

        if self.kill_switch_active:
            log.append("KILL SWITCH ACTIVE — all trading halted")
            self._log(log)
            return self._deny(signal, "Kill switch active", discipline)

        current_minute = datetime.now(timezone.utc).minute
        is_in_execution_window = win_start <= current_minute <= win_end

        if not is_in_execution_window and not self.manual_override:
            deny_reason = f"Candle forming (Min {current_minute:02d}). Window opens at {win_start}-{win_end}."
            deny.append(deny_reason)
            log.append(f"TIME FILTER: {deny_reason}")
            return self._deny(signal, deny_reason, discipline)

        if is_in_execution_window:
            log.append(f"TIME FILTER: PASSED — Minute {current_minute:02d} (window: {win_start}-{win_end})")

        stats = self.db.get_trade_stats(days_back=1)
        daily_pnl = stats["total_pnl"]
        daily_limit = self.portfolio_value * (dyn.max_daily_loss_pct / 100)
        
        if daily_pnl < -daily_limit:
            deny.append(f"Daily loss ${abs(daily_pnl):,.0f} exceeds limit")

        week_stats = self.db.get_trade_stats(days_back=7)
        weekly_limit = self.portfolio_value * (dyn.max_drawdown_pct / 100)
        
        if week_stats["total_pnl"] < -weekly_limit:
            deny.append("CIRCUIT BREAKER — weekly drawdown limit hit")

        # V3.1: Check both OPEN and PENDING trades against the limit
        active_t = self.db.get_active_trades()
        if len(active_t) >= dyn.max_open_positions:
            deny.append(f"Max active/pending positions reached: {len(active_t)}/{dyn.max_open_positions}")

        if signal.bias == Bias.NEUTRAL and not self.manual_override:
            deny.append("No directional bias — standing aside")
            
        if signal.confidence < dyn.min_confidence:
            deny.append(f"Confidence {signal.confidence:.0%} below {dyn.min_confidence:.0%}")
            
        if signal.wick_rejection is None and not self.manual_override:
            deny.append("No wick rejection detected")

        # ── V3.1 Math: Sniper Sizing & Slippage ──
        stop_loss = signal.suggested_sl
        take_profit = signal.suggested_tp
        ideal_entry = signal.sniper_entry_price
        
        # We assume slippage against us when entering
        if signal.bias == Bias.LONG:
            f_entry = ideal_entry * (1 + (dyn.slippage_pct / 100))
        else:
            f_entry = ideal_entry * (1 - (dyn.slippage_pct / 100))
            
        sl_distance = abs(f_entry - stop_loss)
        sl_fraction = sl_distance / f_entry if f_entry > 0 else 0.0

        if (sl_distance / f_entry * 100) > dyn.sl_max_pct:
            warnings_list.append(f"SL capped at {dyn.sl_max_pct}%")
            if signal.bias == Bias.LONG:
                stop_loss = f_entry * (1 - dyn.sl_max_pct / 100)
            elif signal.bias == Bias.SHORT:
                stop_loss = f_entry * (1 + dyn.sl_max_pct / 100)
            sl_distance = abs(f_entry - stop_loss)
            sl_fraction = sl_distance / f_entry

        risk_amount = self.portfolio_value * (dyn.max_risk_per_trade_pct / 100)
        total_fee_friction = (dyn.taker_fee_pct / 100) * 2 
        adjusted_sl_fraction = sl_fraction + total_fee_friction
        
        position_size = risk_amount / adjusted_sl_fraction if adjusted_sl_fraction > 0 else 0.0
        
        max_pos = dyn.max_position_size_usd
        if position_size > max_pos:
            position_size = max_pos
            warnings_list.append(f"Position capped at max size (${max_pos:,.0f})")

        position_pct = (position_size / self.portfolio_value) * 100 if self.portfolio_value > 0 else 0
        log.append(f"Risk ${risk_amount:,.0f} | SL {sl_fraction*100:.2f}% | Adjusted for fees → Size ${position_size:,.0f}")

        # ── V3 Math: Net Risk-Reward ──
        if signal.bias == Bias.LONG:
            gross_reward = take_profit - f_entry
            net_reward = gross_reward - (f_entry * (dyn.taker_fee_pct/100)) - (take_profit * (dyn.maker_fee_pct/100))
            gross_risk = f_entry - stop_loss
            net_risk = gross_risk + (f_entry * (dyn.taker_fee_pct/100)) + (stop_loss * (dyn.taker_fee_pct/100))
        elif signal.bias == Bias.SHORT:
            gross_reward = f_entry - take_profit
            net_reward = gross_reward - (f_entry * (dyn.taker_fee_pct/100)) - (take_profit * (dyn.maker_fee_pct/100))
            gross_risk = stop_loss - f_entry
            net_risk = gross_risk + (f_entry * (dyn.taker_fee_pct/100)) + (stop_loss * (dyn.taker_fee_pct/100))
        else:
            net_reward, net_risk = 0.0, 1.0

        rr = net_reward / net_risk if net_risk > 0 else 0.0
        min_rr = 1.5
        
        if rr < min_rr and signal.bias != Bias.NEUTRAL:
            deny.append(f"Net R:R {rr:.2f}:1 (after fees) below {min_rr:.1f}:1")
        log.append(f"Net R:R {rr:.2f}:1 (Fees accounted)")

        if self.manual_override and "Kill switch active" not in deny:
            signal.bias = Bias.LONG if self.manual_override == "FORCE_BUY" else Bias.SHORT
            log.append(f"MANUAL OVERRIDE: {self.manual_override}")
            deny =[d for d in deny if "No directional bias" not in d and "Candle forming" not in d]
            self.manual_override = None

        approved = len(deny) == 0
        
        if deny:
            log.append("DENIED:")
            for r in deny:
                log.append(f" → {r}")
        else:
            log.append(f"APPROVED: {signal.bias.value} @ ${f_entry:,.0f} | Size ${position_size:,.0f} | SL ${stop_loss:,.0f} | TP ${take_profit:,.0f}")
            
        if warnings_list:
            log.append("Warnings:")
            for w in warnings_list:
                log.append(f" ⚠ {w}")
                
        self._log(log)

        return RiskVerdict(
            approved=approved,
            original_signal=signal,
            position_size_usd=position_size if approved else 0.0,
            position_size_pct=position_pct if approved else 0.0,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr,
            sl_distance_pct=sl_fraction*100,
            reasoning="\n".join(log),
            discipline_rules=discipline,
            warnings=deny if not approved else warnings_list,
        )

    def _deny(self, signal, reason, rules):
        return RiskVerdict(False, signal, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, reason, rules, [reason])

    def _log(self, msgs):
        for m in msgs:
            sev = "warning" if any(x in m for x in["DENIED", "KILL", "CIRCUIT", "TIME FILTER", "Candle forming"]) else "info"
            self.db.add_monologue(
                MonologueEntry(datetime.now(timezone.utc), "Risk Manager", m, sev)
            )

    def set_portfolio_value(self, v: float):
        self.portfolio_value = v

    def activate_kill_switch(self):
        self.kill_switch_active = True
        self.db.add_monologue(MonologueEntry(datetime.now(timezone.utc), "Risk Manager", "KILL SWITCH ACTIVATED", "action"))

    def deactivate_kill_switch(self):
        self.kill_switch_active = False
        self.db.add_monologue(MonologueEntry(datetime.now(timezone.utc), "Risk Manager", "Kill switch deactivated", "action"))

    def set_manual_override(self, action: str):
        self.manual_override = action
        self.db.add_monologue(MonologueEntry(datetime.now(timezone.utc), "Risk Manager", f"MANUAL OVERRIDE: {action}", "override"))
