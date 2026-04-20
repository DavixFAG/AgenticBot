"""
dashboard.py — V3.1 (Institutional Observer UI - Sniper Module)
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import BOT_CONFIG
from data_engine import DataEngine
from database import Database
from orchestrator import Orchestrator

st.set_page_config(page_title="Multi-Agent System", page_icon="◉", layout="wide", initial_sidebar_state="expanded")

# --- UI Styling ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
.stApp { background:#09090b; color:#a1a1aa; font-family:'Inter',sans-serif; }
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#27272a; border-radius:2px; }
section[data-testid="stSidebar"] > div { background:#0c0c0f; }
div[data-testid="stMetric"] { display:none; }
.stTabs [data-baseweb="tab-list"] { gap:0; background:transparent; border-bottom:1px solid #18181b; }
.stTabs [data-baseweb="tab"] { background:transparent; color:#3f3f46; border:none; border-bottom:2px solid transparent; border-radius:0; padding:10px 18px; font-family:'Inter'; font-size:0.78rem; font-weight:500; }
.stTabs [data-baseweb="tab"]:hover { color:#71717a; }
.stTabs [aria-selected="true"] { color:#a1a1aa !important; background:transparent !important; border-bottom:2px solid #3b82f6 !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
.streamlit-expanderHeader { background:#0f0f12; border:1px solid #18181b; border-radius:8px; color:#52525b; font-size:0.78rem; }
.streamlit-expanderContent { background:#0c0c0f; border:1px solid #18181b; border-top:none; }
hr { border-color:#141416; margin:0.8rem 0; }
.sys-title { font-family:'Inter'; font-size:1.1rem; font-weight:700; color:#d4d4d8; }
.sys-sub { font-family:'IBM Plex Mono',monospace; font-size:0.65rem; color:#27272a; margin-top:3px; }
.tags { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
.t { padding:3px 8px; border-radius:4px; font-family:'IBM Plex Mono',monospace; font-size:0.65rem; font-weight:500; border:1px solid; }
.t-on { background:#052e16; color:#4ade80; border-color:#14532d; }
.t-off { background:#141416; color:#52525b; border-color:#1e1e22; }
.t-long { background:#052e16; color:#4ade80; border-color:#14532d; }
.t-short { background:#200a0a; color:#f87171; border-color:#350a0a; }
.t-neutral { background:#1a1805; color:#ca8a04; border-color:#362006; }
.t-n { background:#141416; color:#3f3f46; border-color:#1e1e22; }
.t-kill { background:#200a0a; color:#ef4444; border-color:#450a0a; animation:pulse 1.5s ease-in-out infinite; }
.t-connected { background:#052e16; color:#4ade80; border-color:#14532d; }
.t-offline { background:#200a0a; color:#f87171; border-color:#350a0a; animation:pulse 1.5s ease-in-out infinite; }
.t-waiting { background:#1a1805; color:#ca8a04; border-color:#362006; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.5;} }
.slabel { font-family:'Inter'; font-size:0.62rem; font-weight:600; color:#27272a; text-transform:uppercase; letter-spacing:1.5px; margin:12px 0 8px 0; }
.verdict-card { background:#0f0f12; border:1px solid #18181b; border-radius:16px; padding:32px; text-align:center; margin-bottom:20px; }
.verdict-direction { font-family:'Inter'; font-size:3rem; font-weight:800; letter-spacing:-1px; line-height:1; margin-bottom:8px; }
.verdict-long { color:#4ade80; }
.verdict-short { color:#f87171; }
.verdict-neutral { color:#52525b; }
.verdict-conf { font-family:'IBM Plex Mono',monospace; font-size:0.85rem; margin-top:8px; }
.verdict-sub { font-family:'IBM Plex Mono',monospace; font-size:0.72rem; color:#3f3f46; margin-top:4px; }
.verdict-status { display:inline-block; padding:4px 12px; border-radius:6px; font-family:'IBM Plex Mono',monospace; font-size:0.7rem; font-weight:600; margin-top:12px; letter-spacing:0.5px; }
.vs-approved { background:#052e16; color:#4ade80; border:1px solid #14532d; }
.vs-denied { background:#200a0a; color:#f87171; border:1px solid #350a0a; }
.vs-waiting { background:#1a1805; color:#ca8a04; border:1px solid #362006; }
.cb { display:flex; align-items:center; gap:8px; padding:5px 0; }
.cb-name { font-family:'IBM Plex Mono',monospace; font-size:0.68rem; color:#3f3f46; width:80px; text-align:right; }
.cb-track { flex-grow:1; height:4px; background:#141416; border-radius:2px; overflow:hidden; }
.cb-fill { height:100%; border-radius:2px; transition:width 0.3s ease; }
.cb-val { font-family:'IBM Plex Mono',monospace; font-size:0.68rem; font-weight:600; width:36px; }
.cv-g { color:#4ade80; } .cv-y { color:#eab308; } .cv-r { color:#f87171; }
.reason-box { background:#0c0c0f; border:1px solid #141416; border-radius:8px; padding:14px; margin-top:12px; font-family:'IBM Plex Mono',monospace; font-size:0.72rem; color:#52525b; line-height:1.6; max-height:300px; overflow-y:auto; white-space:pre-wrap; }
.lw { background:#111114; border:1px solid #18181b; border-radius:8px; padding:12px 14px; margin-bottom:6px; }
.lw-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.lw-date { font-family:'IBM Plex Mono',monospace; font-size:0.68rem; color:#3f3f46; }
.lw-regime { font-family:'IBM Plex Mono',monospace; font-size:0.6rem; font-weight:600; padding:2px 6px; border-radius:3px; text-transform:uppercase; letter-spacing:0.8px; }
.rt { background:#052e16; color:#4ade80; } .rr { background:#1a1805; color:#ca8a04; } .rv { background:#200a0a; color:#f87171; }
.lw-stat { font-family:'IBM Plex Mono',monospace; font-size:0.7rem; color:#27272a; margin-bottom:8px; }
.lw-item { padding:4px 0 4px 10px; border-left:2px solid #1e1e22; font-size:0.75rem; color:#52525b; line-height:1.45; margin:2px 0; }
.lw-chg { padding:4px 0 4px 10px; border-left:2px solid #362006; font-family:'IBM Plex Mono',monospace; font-size:0.68rem; color:#ca8a04; margin:2px 0; }
.rl { display:flex; justify-content:space-between; padding:5px 0; font-family:'IBM Plex Mono',monospace; font-size:0.68rem; border-bottom:1px solid #111114; }
.rl:last-child { border-bottom:none; }
.rl-k { color:#27272a; } .rl-v { color:#52525b; font-weight:600; }
.d-pos { color:#4ade80; } .d-neg { color:#f87171; } .d-flat { color:#3f3f46; }
.price-live { display:inline-block; width:6px; height:6px; background:#4ade80; border-radius:50%; margin-right:4px; animation:pdot 2s ease-in-out infinite; }
@keyframes pdot { 0%,100%{opacity:1;} 50%{opacity:0.7;} }
.backend-banner { padding:10px 16px; border-radius:8px; font-family:'IBM Plex Mono',monospace; font-size:0.72rem; margin-bottom:16px; display:flex; align-items:center; gap:10px; }
.backend-ok { background:#052e16; border:1px solid #14532d; color:#4ade80; }
.backend-warn { background:#1a1805; border:1px solid #362006; color:#ca8a04; }
.backend-err { background:#200a0a; border:1px solid #350a0a; color:#f87171; }
</style>
""", unsafe_allow_html=True)

def _check_backend_health(db: Database) -> tuple[str, str, str]:
    try:
        recent = db.get_monologue(limit=1)
        if not recent:
            return "No Data", "t-waiting", "backend-warn"
            
        ts_str = recent[-1].get("timestamp", "")
        if not ts_str:
            return "No Timestamp", "t-waiting", "backend-warn"
            
        last_ts = datetime.fromisoformat(ts_str)
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
            
        age_seconds = (datetime.now(timezone.utc) - last_ts).total_seconds()
        
        if age_seconds <= 90:
            return "🟢 Backend Connected", "t-connected", "backend-ok"
        elif age_seconds <= 300:
            return f"🟡 Last seen {int(age_seconds//60)}m {int(age_seconds%60)}s ago", "t-waiting", "backend-warn"
        else:
            return "🔴 Backend Offline", "t-offline", "backend-err"
    except Exception:
        return "🔴 Cannot Read DB", "t-offline", "backend-err"

def simplify(msg):
    for e in["⚡", "🔥", "📊", "📌", "📚", "🔄", "⚠️", "✅", "❌", "🛑", "📈", "🎓", "🚀", "📡", "🛡️", "🔭", "📋", "💡", "🔧", "📅"]:
        msg = msg.replace(e, "")
    return msg.strip()[:150]

# --- State Management ---
if "db" not in st.session_state:
    st.session_state.db = Database(BOT_CONFIG.db_path)
if "data_engine" not in st.session_state:
    st.session_state.data_engine = DataEngine()
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "orch" not in st.session_state:
    st.session_state.orch = Orchestrator()

db: Database = st.session_state.db
de: DataEngine = st.session_state.data_engine
orch: Orchestrator = st.session_state.orch

state = orch.get_current_state()
backend_status, backend_tag_cls, backend_banner_cls = _check_backend_health(db)

try:
    live_price = de.get_live_price()
    price_src = "live"
except Exception:
    live_price = state["last_signal"]["indicators"]["price"] if state["last_signal"] else 0
    price_src = "cached"
    
now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S")
current_minute = datetime.now(timezone.utc).minute

dyn = state["dynamic_config"]
win_start = dyn.get('execution_window_start', 57)
win_end = dyn.get('execution_window_end', 59)

# --- Header ---
h1, h2 = st.columns([2, 3])
with h1:
    st.markdown(
        '<div style="padding:20px 0 16px 0;">'
        '<div class="sys-title">Institutional Trading System</div>'
        '<div class="sys-sub">BTC/USD · V3.1 Sniper Module · JSON IPC</div>'
        '</div>', 
        unsafe_allow_html=True
    )
    
with h2:
    bias = state.get("current_bias", "NEUTRAL")
    b_cls = {"LONG": "t-long", "SHORT": "t-short", "NEUTRAL": "t-neutral"}.get(bias, "t-neutral")
    kill_tag = '<span class="t t-kill">kill active</span>' if state["kill_switch"] else ""
    
    in_window = win_start <= current_minute <= win_end
    window_cls = "t-on" if in_window else "t-neutral"
    window_txt = f"exec: min {current_minute:02d} {'✓' if in_window else '…'}"
    
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;padding-top:24px;">'
        f'<div class="tags">'
        f'<span class="t {backend_tag_cls}">{backend_status}</span>'
        f'<span class="t {b_cls}">{bias.lower()}</span>'
        f'<span class="t {window_cls}">{window_txt}</span>'
        f'<span class="t t-n">#{state["cycle_count"]}</span>'
        f'{kill_tag}'
        f'</div></div>', 
        unsafe_allow_html=True
    )
    
st.markdown(
    f'<div class="backend-banner {backend_banner_cls}">'
    f'<span>{backend_status}</span>'
    f'<span style="color:#3f3f46;">|</span>'
    f'<span>Run bot: <code>python main.py</code></span>'
    f'<span style="color:#3f3f46;">|</span>'
    f'<span>Dynamic Execution Window: Min {win_start}-{win_end}</span>'
    f'</div>', 
    unsafe_allow_html=True
)

# --- Stats Bar ---
s7 = state["trade_stats_7d"]
s30 = state["trade_stats_30d"]
pnl7 = s7["total_pnl"]
pc = "d-pos" if pnl7 > 0 else "d-neg" if pnl7 < 0 else "d-flat"
ps = "+" if pnl7 > 0 else ""
wr = s7["win_rate"]
pd_cls = "price-live" if price_src == "live" else ""

st.markdown(
    f'<div style="display:flex;gap:1px;background:#18181b;border:1px solid #18181b;border-radius:12px;overflow:hidden;margin-bottom:20px;">'
    f'<div style="flex:1;background:#0f0f12;padding:16px 20px;">'
    f'<div style="font-family:Inter;font-size:0.6rem;font-weight:600;color:#3f3f46;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">BTC / USD</div>'
    f'<div style="font-family:IBM Plex Mono,monospace;font-size:1.15rem;font-weight:600;color:#e4e4e7;"><span class="{pd_cls}"></span>${live_price:,.2f}</div>'
    f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;margin-top:4px;color:#3f3f46;">{now_utc} UTC</div>'
    f'</div>'
    f'<div style="flex:1;background:#0f0f12;padding:16px 20px;">'
    f'<div style="font-family:Inter;font-size:0.6rem;font-weight:600;color:#3f3f46;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Win Rate (7D)</div>'
    f'<div style="font-family:IBM Plex Mono,monospace;font-size:1.15rem;font-weight:600;color:#e4e4e7;">{wr:.0%}</div>'
    f'<div class="d-flat" style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;margin-top:4px;">{s7["wins"]}W · {s7["losses"]}L</div>'
    f'</div>'
    f'<div style="flex:1;background:#0f0f12;padding:16px 20px;">'
    f'<div style="font-family:Inter;font-size:0.6rem;font-weight:600;color:#3f3f46;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">P&L (7D)</div>'
    f'<div style="font-family:IBM Plex Mono,monospace;font-size:1.15rem;font-weight:600;color:#e4e4e7;">{ps}${abs(pnl7):,.2f}</div>'
    f'<div class="{pc}" style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;margin-top:4px;">{"profit" if pnl7 > 0 else "loss" if pnl7 < 0 else "flat"}</div>'
    f'</div>'
    f'<div style="flex:1;background:#0f0f12;padding:16px 20px;">'
    f'<div style="font-family:Inter;font-size:0.6rem;font-weight:600;color:#3f3f46;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Trades (30D)</div>'
    f'<div style="font-family:IBM Plex Mono,monospace;font-size:1.15rem;font-weight:600;color:#e4e4e7;">{s30["total"]}</div>'
    f'<div class="d-flat" style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;margin-top:4px;">{s30["wins"]}W · {s30["losses"]}L</div>'
    f'</div>'
    f'<div style="flex:1;background:#0f0f12;padding:16px 20px;">'
    f'<div style="font-family:Inter;font-size:0.6rem;font-weight:600;color:#3f3f46;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Active</div>'
    f'<div style="font-family:IBM Plex Mono,monospace;font-size:1.15rem;font-weight:600;color:#e4e4e7;">{len(state["active_trades"])}</div>'
    f'<div class="d-flat" style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;margin-top:4px;">orders</div>'
    f'</div>'
    f'</div>', 
    unsafe_allow_html=True
)

# --- Sidebar ---
with st.sidebar:
    st.markdown("**System**")
    st.markdown(
        f'<div style="padding:8px 0;">'
        f'<div class="t {backend_tag_cls}" style="display:inline-block;margin-bottom:6px;">{backend_status}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#27272a;margin-top:4px;">Start bot: <code>python main.py</code></div>'
        f'</div>', 
        unsafe_allow_html=True
    )
    
    kill_on = st.toggle("Kill Switch", value=state["kill_switch"])
    if kill_on and not state["kill_switch"]:
        orch.activate_kill_switch()
        st.rerun()
    elif not kill_on and state["kill_switch"]:
        orch.deactivate_kill_switch()
        st.rerun()
        
    st.session_state.auto_refresh = st.toggle("Auto-refresh (10s)", value=st.session_state.auto_refresh)
    st.divider()
    
    st.markdown("**Execution Window**")
    mins_to_window = max(0, win_start - current_minute)
    
    if in_window:
        st.markdown(
            '<div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#4ade80;">'
            '🟢 OPEN — Executing if viable'
            '</div>', 
            unsafe_allow_html=True
        )
    elif current_minute > win_end:
        st.markdown(
            '<div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#f87171;">'
            '🔴 MISSED — Reopens next hour'
            '</div>', 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#ca8a04;">'
            f'🔴 CLOSED — Opens in {mins_to_window} min'
            f'</div>', 
            unsafe_allow_html=True
        )
        
    st.divider()
    
    # V3.1 Removed manual Buy/Sell buttons to enforce institutional discipline.
    st.markdown("**Quick Actions**")
    c_scan, c_review = st.columns(2)
    with c_scan:
        if st.button("Force Scan", use_container_width=True):
            orch.force_scan()
            st.rerun()
    with c_review:
        if st.button("Force Review", use_container_width=True):
            orch.force_scholar_review()
            st.rerun()
            
    st.divider()
    st.markdown("**Reset Tracking**")
    confirm_reset = st.text_input("Type RESET to enable", value="")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Clear Trades", use_container_width=True):
            if confirm_reset == "RESET":
                try:
                    orch.reset_portfolio_tracking(full_reset=False)
                    st.success("Trade history cleared.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Type RESET first.")
    with c2:
        if st.button("Full Reset", use_container_width=True):
            if confirm_reset == "RESET":
                try:
                    orch.reset_portfolio_tracking(full_reset=True)
                    st.success("All system data cleared.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Type RESET first.")
                
    st.divider()
    st.markdown("**Notifications**")
    if st.button("Test Notification", use_container_width=True):
        orch.notifier.test()
        st.toast("Notification sent")
        
    st.divider()
    st.markdown("**Active Rules**")
    rules = [
        ("risk/trade", f"{dyn['max_risk_per_trade_pct']}%"),
        ("daily cap", f"{dyn['max_daily_loss_pct']}%"),
        ("drawdown", f"{dyn['max_drawdown_pct']}%"),
        ("sl max", f"{dyn.get('sl_max_pct', 1.5)}%"),
        ("confidence", f"{dyn.get('min_confidence', 0.55):.0%}"),
        ("exec window", f"Min {win_start}-{win_end}"),
        ("friction", f"S: {dyn.get('slippage_pct', 0.05)}% F: {dyn.get('taker_fee_pct', 0.05)}%")
    ]
    for k, v in rules:
        st.markdown(
            f'<div class="rl"><span class="rl-k">{k}</span><span class="rl-v">{v}</span></div>', 
            unsafe_allow_html=True
        )

# --- Chart Data Prep ---
chart_df = None
chart_error = None
try:
    chart_df = de.fetch_ohlcv(BOT_CONFIG.timeframes.primary, 120)
    chart_df = de.compute_indicators(chart_df)
except Exception as e:
    chart_error = str(e)

tab1, tab2, tab3, tab4 = st.tabs(["Verdict", "Chart", "Learning", "Trades"])

# ─── TAB 1: VERDICT ───
with tab1:
    sig = state["last_signal"]
    vrd = state["last_verdict"]
    
    if sig and vrd:
        direction = sig.get("bias", "NEUTRAL")
        d_cls = {
            "LONG": "verdict-long", 
            "SHORT": "verdict-short", 
            "NEUTRAL": "verdict-neutral"
        }.get(direction, "verdict-neutral")
        
        if vrd.get("approved"):
            st_cls, st_txt = "vs-approved", "APPROVED — TRADE ACTIVE"
        elif direction == "NEUTRAL":
            st_cls, st_txt = "vs-waiting", "WAITING — NO CLEAR EDGE"
        else:
            if any("Candle forming" in r for r in vrd.get("warnings",[])):
                st_cls, st_txt = "vs-waiting", f"WATCHING — Opens min {win_start}"
            else:
                st_cls, st_txt = "vs-denied", "DENIED — RISK RULES"
                
        conf = sig.get("confidence", 0)
        cc = "d-pos" if conf > 0.6 else "d-neg" if conf < 0.4 else "d-flat"
        npat = len(sig.get("patterns_detected",[]))
        
        st.markdown(
            f'<div class="verdict-card">'
            f'<div class="verdict-direction {d_cls}">{direction}</div>'
            f'<div class="verdict-conf {cc}">{conf:.0%} confidence</div>'
            f'<div class="verdict-sub">{npat} pattern(s) detected</div>'
            f'<div class="verdict-status {st_cls}">{st_txt}</div>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        if vrd.get("approved") or direction != "NEUTRAL":
            sl = vrd.get("stop_loss") or sig.get("suggested_sl", 0)
            tp = vrd.get("take_profit") or sig.get("suggested_tp", 0)
            rr = vrd.get("risk_reward_ratio", 0)
            
            # V3.1 Display the Sniper Entry 
            ep = sig.get("sniper_entry_price", sig.get("entry_price", 0))
            
            st.markdown(
                f'<div style="display:flex;gap:1px;background:#18181b;border:1px solid #18181b;border-radius:10px 10px 0 0;overflow:hidden;">'
                f'<div style="flex:1;background:#0f0f12;padding:12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Target Entry</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.9rem;font-weight:600;color:#a1a1aa;">${ep:,.2f}</div>'
                f'</div>'
                f'<div style="flex:1;background:#0f0f12;padding:12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Stop Loss</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.9rem;font-weight:600;color:#f87171;">${sl:,.2f}</div>'
                f'</div>'
                f'<div style="flex:1;background:#0f0f12;padding:12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Take Profit</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.9rem;font-weight:600;color:#4ade80;">${tp:,.2f}</div>'
                f'</div>'
                f'<div style="flex:1;background:#0f0f12;padding:12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Net R : R</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.9rem;font-weight:600;color:#a1a1aa;">{rr:.1f} : 1</div>'
                f'</div>'
                f'</div>', 
                unsafe_allow_html=True
            )
            
        wick = sig.get("wick_rejection")
        if wick:
            wc = "#4ade80" if wick.get("direction") == "bullish" else "#f87171"
            st.markdown(
                f'<div style="background:#111114;border:1px solid #1a1a1e;border-radius:10px;padding:14px 18px;margin-top:12px;">'
                f'<div style="font-family:Inter;font-size:0.68rem;font-weight:600;color:#3f3f46;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Wick Rejection</div>'
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-family:IBM Plex Mono,monospace;font-size:0.72rem;">'
                f'<span style="color:#3f3f46;">Direction</span><span style="color:{wc};font-weight:600;">{wick.get("direction")}</span></div>'
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-family:IBM Plex Mono,monospace;font-size:0.72rem;">'
                f'<span style="color:#3f3f46;">Level</span><span style="color:#71717a;font-weight:600;">${wick.get("rejected_level",0):,.2f} ({wick.get("level_type")})</span></div>'
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-family:IBM Plex Mono,monospace;font-size:0.72rem;">'
                f'<span style="color:#3f3f46;">Wick/Body</span><span style="color:#71717a;font-weight:600;">{wick.get("wick_ratio",0):.1f}x</span></div>'
                f'</div>', 
                unsafe_allow_html=True
            )
            
        if sig.get("confidence_breakdown"):
            st.markdown('<div class="slabel" style="margin-top:16px;">Confidence Breakdown</div>', unsafe_allow_html=True)
            bh = ""
            for name, score in sig["confidence_breakdown"].items():
                if score > 0.65:
                    fc, vc = "#22c55e", "cv-g"
                elif score > 0.45:
                    fc, vc = "#eab308", "cv-y"
                else:
                    fc, vc = "#ef4444", "cv-r"
                    
                bh += (
                    f'<div class="cb">'
                    f'<span class="cb-name">{name.replace("_", " ")}</span>'
                    f'<div class="cb-track">'
                    f'<div class="cb-fill" style="width:{max(2, score*100)}%;background:{fc};"></div>'
                    f'</div>'
                    f'<span class="cb-val {vc}">{score:.0%}</span>'
                    f'</div>'
                )
            st.markdown(bh, unsafe_allow_html=True)
            
        with st.expander("Scout Reasoning"):
            st.markdown(f'<div class="reason-box">{sig.get("reasoning", "")}</div>', unsafe_allow_html=True)
            
        if vrd.get("reasoning"):
            with st.expander("Risk Manager Reasoning"):
                st.markdown(f'<div class="reason-box">{vrd["reasoning"]}</div>', unsafe_allow_html=True)
                
        if not vrd.get("approved") and vrd.get("warnings"):
            st.markdown('<div class="slabel" style="margin-top:12px;">Denied Because</div>', unsafe_allow_html=True)
            dh = ""
            for w in vrd["warnings"]:
                c = simplify(w)
                if c:
                    is_time = "Candle forming" in w
                    border_col = "#362006" if is_time else "#450a0a"
                    bg_col = "#1a1200" if is_time else "#150808"
                    txt_col = "#ca8a04" if is_time else "#f87171"
                    
                    dh += (
                        f'<div style="padding:6px 12px;margin:3px 0;'
                        f'border-left:2px solid {border_col};border-radius:0 4px 4px 0;'
                        f'background:{bg_col};font-family:IBM Plex Mono,monospace;'
                        f'font-size:0.72rem;color:{txt_col};">{c}</div>'
                    )
            if dh:
                st.markdown(dh, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="verdict-card">'
            '<div class="verdict-direction verdict-neutral">—</div>'
            '<div class="verdict-sub">Waiting for backend scan...</div>'
            '<div class="verdict-status vs-waiting">INITIALIZING</div>'
            '</div>', 
            unsafe_allow_html=True
        )

# ─── TAB 2: CHART ───
with tab2:
    if chart_df is not None and len(chart_df) > 0:
        df = chart_df
        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True, 
            vertical_spacing=0.03, row_heights=[0.50, 0.15, 0.15, 0.20]
        )
        
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"], 
            name="BTC/USD", 
            increasing_line_color="#22c55e", decreasing_line_color="#ef4444", 
            increasing_fillcolor="rgba(34,197,94,0.8)", decreasing_fillcolor="rgba(239,68,68,0.8)", 
            line=dict(width=1)
        ), row=1, col=1)
        
        if "ma20" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], name="MA 20", line=dict(color="rgba(59,130,246,0.7)", width=1.2)), row=1, col=1)
        if "ma50" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["ma50"], name="MA 50", line=dict(color="rgba(245,158,11,0.7)", width=1.2)), row=1, col=1)
            
        if "BBU" in df.columns and "BBL" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["BBU"], name="BB Upper", line=dict(color="rgba(99,102,241,0.4)", width=0.8, dash="dot"), showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["BBL"], name="Bollinger", line=dict(color="rgba(99,102,241,0.4)", width=0.8, dash="dot"), fill="tonexty", fillcolor="rgba(99,102,241,0.04)"), row=1, col=1)
            
        if state["last_signal"]:
            sup = state["last_signal"].get("nearest_support", 0)
            res = state["last_signal"].get("nearest_resistance", 0)
            
            fig.add_hline(y=sup, line_dash="dash", line_color="rgba(34,197,94,0.35)", annotation_text=f"S {sup:,.0f}", annotation_font_color="#27272a", annotation_font_size=10, row=1, col=1)
            fig.add_hline(y=res, line_dash="dash", line_color="rgba(239,68,68,0.35)", annotation_text=f"R {res:,.0f}", annotation_font_color="#27272a", annotation_font_size=10, row=1, col=1)
            fig.add_hline(y=live_price, line_dash="dot", line_color="rgba(255,255,255,0.12)", annotation_text=f"${live_price:,.0f}", annotation_font_color="#3f3f46", annotation_font_size=9, row=1, col=1)
            
        if state["last_signal"] and state["last_signal"].get("wick_rejection"):
            wr_obj = state["last_signal"]["wick_rejection"]
            mc = "#4ade80" if wr_obj.get("direction") == "bullish" else "#f87171"
            
            marker_y = wr_obj.get("candle_low") if wr_obj.get("direction") == "bullish" else wr_obj.get("candle_high")
            symbol = "triangle-up" if wr_obj.get("direction") == "bullish" else "triangle-down"
            position = "top center" if wr_obj.get("direction") == "bearish" else "bottom center"
            
            fig.add_trace(go.Scatter(
                x=[wr_obj.get("timestamp")], 
                y=[marker_y], 
                mode="markers+text", 
                marker=dict(symbol=symbol, size=12, color=mc, line=dict(width=1, color="#09090b")), 
                text=["WICK"], 
                textposition=position, 
                textfont=dict(size=8, color=mc), 
                name=f"Wick", 
                showlegend=True
            ), row=1, col=1)
            
        # V3.1: Support PENDING trades rendering
        for ot in state["active_trades"]:
            stat = ot.get("status")
            if stat == "OPEN":
                entry_color = "rgba(59,130,246,0.4)"
                line_style = "solid"
            else:
                entry_color = "rgba(245,158,11,0.6)"
                line_style = "dash"

            if ot.get("entry_price"):
                fig.add_hline(y=ot["entry_price"], line_dash=line_style, line_color=entry_color, line_width=1, row=1, col=1)
            if ot.get("stop_loss"):
                fig.add_hline(y=ot["stop_loss"], line_dash="dot", line_color="rgba(248,113,113,0.5)", line_width=1, row=1, col=1)
            if ot.get("take_profit"):
                fig.add_hline(y=ot["take_profit"], line_dash="dot", line_color="rgba(74,222,128,0.5)", line_width=1, row=1, col=1)
                
        if "volume" in df.columns:
            vol_colors =["rgba(34,197,94,0.35)" if c >= o else "rgba(239,68,68,0.35)" for c, o in zip(df["close"], df["open"])]
            fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=vol_colors, showlegend=False), row=2, col=1)
            
        if "rsi" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI", line=dict(color="#3b82f6", width=1.2)), row=3, col=1)
            fig.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.04)", line_width=0, row=3, col=1)
            fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.04)", line_width=0, row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="#1a1a1e", row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="#1a1a1e", row=3, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="#111114", row=3, col=1)
            
        if "MACDh" in df.columns:
            hist_colors =["#22c55e" if v >= 0 else "#ef4444" for v in df["MACDh"].fillna(0)]
            fig.add_trace(go.Bar(x=df.index, y=df["MACDh"], name="Histogram", marker_color=hist_colors, opacity=0.6, showlegend=False), row=4, col=1)
            
        if "MACD" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#3b82f6", width=1)), row=4, col=1)
            
        if "MACDs" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["MACDs"], name="Signal", line=dict(color="#f59e0b", width=1)), row=4, col=1)
            
        fig.update_layout(
            template="plotly_dark", 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="#0b0b0f", 
            height=680, 
            showlegend=True, 
            legend=dict(orientation="h", y=1.01, x=0.5, xanchor="center", font=dict(size=9, color="#3f3f46"), bgcolor="rgba(0,0,0,0)"), 
            margin=dict(l=55, r=15, t=20, b=15), 
            xaxis_rangeslider_visible=False, 
            font=dict(family="IBM Plex Mono", color="#27272a", size=10)
        )
        
        for ax in["xaxis", "xaxis2", "xaxis3", "xaxis4", "yaxis", "yaxis2", "yaxis3", "yaxis4"]:
            fig.update_layout(**{ax: dict(gridcolor="#111114", zeroline=False)})
            
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Chart unavailable — {chart_error or 'no data'}")

# ─── TAB 3: LEARNING ───
with tab3:
    st.markdown('<div class="slabel">Meta-Strategy Updates</div>', unsafe_allow_html=True)
    
    if state["scholar_reviews"]:
        for rev in state["scholar_reviews"][:5]:
            lessons = json.loads(rev.get("lessons", "[]"))
            changes = json.loads(rev.get("parameter_changes", "{}"))
            
            # V3.1 Fix for f-string dictionary bracket syntax issue
            regime = rev.get("market_regime", "unknown")
            rc = {"trending": "rt", "ranging": "rr", "volatile": "rv"}.get(regime, "rr")
            
            html = (
                f'<div class="lw"><div class="lw-top">'
                f'<span class="lw-date">{rev.get("timestamp", "")[:10]} · {rev.get("total_trades", 0)} trades</span>'
                f'<span class="lw-regime {rc}">{regime}</span>'
                f'</div><div class="lw-stat">{rev.get("win_rate", 0):.0%} win rate · ${rev.get("total_pnl", 0):,.2f}</div>'
            )
            
            for lesson in lessons:
                html += f'<div class="lw-item">{simplify(lesson)}</div>'
                
            if changes:
                parts = " · ".join(f"{k}: {v.get('old', '?')} → {v.get('new', '?')}" for k, v in changes.items())
                html += f'<div class="lw-chg">{parts}</div>'
                
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.caption("No reviews yet.")

# ─── TAB 4: TRADES ───
with tab4:
    st.markdown('<div class="slabel">Active Orders (Open & Pending)</div>', unsafe_allow_html=True)
    opens = state["active_trades"]
    
    if opens:
        if st.button("Close/Cancel All", use_container_width=True):
            orch.close_all_trades()
            st.rerun()
            
        open_html = ""
        for t in opens:
            b = t.get("bias", "NEUTRAL")
            entry = t.get("entry_price", 0)
            sl = t.get("stop_loss", 0)
            tp = t.get("take_profit", 0)
            size = t.get("position_size_usd", 0)
            tid = t.get("id", "—")
            ts_o = str(t.get("timestamp_open", ""))[:16].replace("T", " ")
            stat = t.get("status", "OPEN")
            
            if stat == "PENDING":
                bc, arrow, bbg, bbd = ("#ca8a04", "⌛", "rgba(245,158,11,0.06)", "rgba(245,158,11,0.15)")
            elif b == "LONG":
                bc, arrow, bbg, bbd = ("#4ade80", "↑", "rgba(74,222,128,0.06)", "rgba(74,222,128,0.15)")
            elif b == "SHORT":
                bc, arrow, bbg, bbd = ("#f87171", "↓", "rgba(248,113,113,0.06)", "rgba(248,113,113,0.15)")
            else:
                bc, arrow, bbg, bbd = ("#a1a1aa", "–", "rgba(161,161,170,0.06)", "rgba(161,161,170,0.15)")
                
            if stat == "OPEN" and live_price > 0 and entry > 0:
                if b == "LONG":
                    up = ((live_price - entry) / entry) * 100
                elif b == "SHORT":
                    up = ((entry - live_price) / entry) * 100
                else:
                    up = 0
                uc = "#4ade80" if up >= 0 else "#f87171"
                ut = f"{'+' if up >= 0 else ''}${abs(size*(up/100)):,.2f} ({'+' if up >= 0 else ''}{up:.2f}%)"
                sub_txt = f"unrealized · ${live_price:,.0f}"
            else:
                uc, ut = "#ca8a04", "LIMIT ORDER"
                sub_txt = f"waiting for fill"

            open_html += (
                f'<div style="background:{bbg};border:1px solid {bbd};border-radius:12px;padding:16px 20px;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-family:IBM Plex Mono,monospace;font-size:1.4rem;font-weight:700;color:{bc};">{arrow} {b}</span>'
                f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#3f3f46;background:#141416;padding:2px 8px;border-radius:4px;">{tid}</span>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.95rem;font-weight:700;color:{uc};">{ut}</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.58rem;color:#27272a;">{sub_txt}</div>'
                f'</div>'
                f'</div>'
                f'<div style="display:flex;gap:1px;background:#18181b;border-radius:8px;overflow:hidden;">'
                f'<div style="flex:1;background:#0f0f12;padding:10px 12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Entry</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.82rem;font-weight:600;color:#a1a1aa;">${entry:,.2f}</div>'
                f'</div>'
                f'<div style="flex:1;background:#0f0f12;padding:10px 12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Stop Loss</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.82rem;font-weight:600;color:#f87171;">${sl:,.2f}</div>'
                f'</div>'
                f'<div style="flex:1;background:#0f0f12;padding:10px 12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Take Profit</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.82rem;font-weight:600;color:#4ade80;">${tp:,.2f}</div>'
                f'</div>'
                f'<div style="flex:1;background:#0f0f12;padding:10px 12px;text-align:center;">'
                f'<div style="font-family:Inter;font-size:0.52rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Size</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.82rem;font-weight:600;color:#a1a1aa;">${size:,.0f}</div>'
                f'</div>'
                f'</div>'
                f'</div>'
            )
            
        st.markdown(open_html, unsafe_allow_html=True)
        st.markdown('<div class="slabel" style="margin-top:8px;">Close Individual</div>', unsafe_allow_html=True)
        
        cols = st.columns(min(len(opens), 4))
        for idx, t in enumerate(opens):
            with cols[idx % min(len(opens), 4)]:
                action_text = "Cancel" if t.get('status') == 'PENDING' else "Close"
                btn_label = f"{action_text} {t.get('bias', '—')[0]}·{t.get('id', '—')[:4]}"
                if st.button(btn_label, key=f"c_{t.get('id')}", use_container_width=True):
                    orch.close_trade_manually(t.get('id'))
                    st.rerun()
    else:
        st.markdown(
            '<div style="text-align:center;padding:32px 16px;color:#1e1e22;font-family:Inter;font-size:0.8rem;">No open or pending positions</div>', 
            unsafe_allow_html=True
        )

    st.markdown('<div class="slabel" style="margin-top:24px;">Recent Closed</div>', unsafe_allow_html=True)
    closed = [t for t in db.get_trades(30) if t["status"] == "CLOSED"]
    
    if closed:
        ch = ""
        for t in closed[:15]:
            pnl = t.get("pnl_usd") or 0
            iw = pnl > 0
            
            if t.get("bias") == "LONG":
                bc, arrow = "#4ade80", "↑"
            elif t.get("bias") == "SHORT":
                bc, arrow = "#f87171", "↓"
            else:
                bc, arrow = "#a1a1aa", "–"
                
            if iw:
                rc, rbg, rbd, ri = "#4ade80", "rgba(74,222,128,0.04)", "rgba(74,222,128,0.10)", "✓"
            else:
                rc, rbg, rbd, ri = "#f87171", "rgba(248,113,113,0.04)", "rgba(248,113,113,0.10)", "✗"
                
            ch += (
                f'<div style="background:{rbg};border:1px solid {rbd};border-radius:10px;padding:12px 16px;margin-bottom:4px;display:flex;align-items:center;gap:12px;">'
                f'<div style="min-width:75px;"><span style="font-family:IBM Plex Mono,monospace;font-size:0.9rem;font-weight:700;color:{bc};">{arrow} {t.get("bias", "—")}</span></div>'
                f'<div style="flex:1;">'
                f'<div style="font-family:Inter;font-size:0.5rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:0.8px;">Entry → Exit</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.78rem;color:#71717a;">${t.get("entry_price",0):,.2f} → ${t.get("exit_price",0):,.2f}</div>'
                f'</div>'
                f'<div style="flex:0.7;">'
                f'<div style="font-family:Inter;font-size:0.5rem;font-weight:600;color:#27272a;text-transform:uppercase;letter-spacing:0.8px;">P&L</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.85rem;font-weight:700;color:{rc};">{ri} {"+" if iw else ""}${abs(pnl):,.2f}</div>'
                f'</div>'
                f'<div style="min-width:100px;text-align:right;">'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#27272a;">{str(t.get("timestamp_close", ""))[:16].replace("T", " ")}</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.55rem;color:#1e1e22;">{t.get("id", "—")}</div>'
                f'</div>'
                f'</div>'
            )
        st.markdown(ch, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="text-align:center;padding:32px 16px;color:#1e1e22;font-family:Inter;font-size:0.8rem;">No closed trades yet</div>', 
            unsafe_allow_html=True
        )

# --- Auto-Refresh ---
if st.session_state.auto_refresh:
    time.sleep(10)
    st.rerun()
