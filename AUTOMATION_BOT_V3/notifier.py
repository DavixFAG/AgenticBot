import base64
import logging
import os
import subprocess
import sys
import threading
import requests
from typing import Optional
from dotenv import load_dotenv

from config import BOT_CONFIG

load_dotenv()
log = logging.getLogger(__name__)

class Notifier:
    SOUND_TRADE = "ms-winsoundevent:Notification.Mail"
    SOUND_WIN = "ms-winsoundevent:Notification.Mail"
    SOUND_LOSS = "ms-winsoundevent:Notification.Reminder"
    SOUND_URGENT = "ms-winsoundevent:Notification.Looping.Alarm"
    SOUND_SIGNAL = "ms-winsoundevent:Notification.Default"
    SOUND_SILENT = "silent"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._ps: Optional[str] = None
        self._is_wsl = False
        self.toast_enabled = False
        
        if self.enabled:
            self._detect_environment()
            self._ps = self._find_powershell()
            if not self._ps:
                log.info("[Notifier] PowerShell not found. Desktop Toasts disabled.")
            else:
                self.toast_enabled = True
                log.info(f"[Notifier] Desktop Toasts Active ({'WSL' if self._is_wsl else 'Native'})")

    @property
    def tg_token(self):
        return os.getenv("TELEGRAM_BOT_TOKEN", "").strip("'\" ")
        
    @property
    def tg_chat_id(self):
        return os.getenv("TELEGRAM_CHAT_ID", "").strip("'\" ")
        
    @property
    def tg_enabled(self):
        return bool(self.tg_token and self.tg_chat_id)

    def trade_setup(self, bias: str, entry: float, sl: float, tp: float, confidence: float):
        self._dispatch(
            f"🔔 Setup Ready: {'↑' if bias == 'LONG' else '↓'} {bias} ({confidence:.0%})", 
            f"Entry: ${entry:,.2f}\nSL: ${sl:,.2f}\nTP: ${tp:,.2f}\nConfidence: {confidence:.0%}", 
            self.SOUND_SIGNAL, 
            f"🔔 <b>Setup Ready:</b> {'🟢' if bias == 'LONG' else '🔴'} <b>{bias}</b>\nConfidence: {confidence:.0%}\n\nEntry: <code>${entry:,.2f}</code>\nSL: <code>${sl:,.2f}</code>\nTP: <code>${tp:,.2f}</code>"
        )

    def trade_opened(self, bias: str, entry: float, sl: float, tp: float, rr: float, size: float, trade_id: str, sl_pct: float):
        self._dispatch(
            f"✅ {'↑' if bias == 'LONG' else '↓'} {bias} Trade Opened", 
            f"Entry: ${entry:,.2f}\nSL: ${sl:,.2f} ({sl_pct:.2f}%)\nTP: ${tp:,.2f}\nSize: ${size:,.0f} | R:R {rr:.1f}:1\nID: {trade_id}", 
            self.SOUND_TRADE, 
            f"🚀 <b>TRADE OPENED:</b> {'🟢' if bias == 'LONG' else '🔴'} <b>{bias}</b>\nID: <code>{trade_id}</code>\n\nSize: <code>${size:,.0f}</code> | R:R <code>{rr:.1f}:1</code>\nEntry: <code>${entry:,.2f}</code>\nSL: <code>${sl:,.2f}</code> ({sl_pct:.2f}%)\nTP: <code>${tp:,.2f}</code>"
        )

    def trade_closed(self, bias: str, entry: float, exit_price: float, pnl_usd: float, pnl_pct: float, reason: str, trade_id: str):
        is_win = pnl_usd > 0
        icon = "✅" if is_win else "❌"
        word = "Won" if is_win else "Lost"
        sign = "+" if pnl_usd > 0 else ""
        
        self._dispatch(
            f"{icon} {word} {sign}${abs(pnl_usd):,.2f} ({sign}{pnl_pct:.2f}%)", 
            f"{'↑' if bias == 'LONG' else '↓'} {bias}\nEntry: ${entry:,.2f}\nExit: ${exit_price:,.2f}\nReason: {reason}\nID: {trade_id}", 
            self.SOUND_WIN if is_win else self.SOUND_LOSS, 
            f"{icon} <b>TRADE {word.upper()}:</b> <b>{bias}</b>\nP&L: <b>{sign}${pnl_usd:,.2f}</b> ({sign}{pnl_pct:.2f}%)\n\nReason: {reason}\nEntry: <code>${entry:,.2f}</code>\nExit: <code>${exit_price:,.2f}</code>\nID: <code>{trade_id}</code>"
        )

    def trailing_stop_moved(self, bias: str, trade_id: str, old_sl: float, new_sl: float, price: float):
        self._dispatch(
            "↕ Trailing SL Updated", 
            f"{bias} {trade_id[:8]}\nSL: ${old_sl:,.2f} → ${new_sl:,.2f}\nPrice: ${price:,.2f}", 
            self.SOUND_SILENT, 
            f"🛡️ <b>Trailing SL Updated</b> ({bias})\nID: <code>{trade_id[:8]}</code>\n\nPrice: <code>${price:,.2f}</code>\nSL Moved: <code>${old_sl:,.2f}</code> ➡️ <code>${new_sl:,.2f}</code>"
        )

    def signal_detected(self, bias: str, confidence: float, price: float, patterns: int):
        self._dispatch(
            f"🔔 Signal: {'↑' if bias == 'LONG' else '↓'} {bias} @ {confidence:.0%}", 
            f"BTC: ${price:,.2f}\nPatterns: {patterns}\nAwaiting risk approval...", 
            self.SOUND_SIGNAL, 
            f"👀 <b>Signal Detected:</b> {'🟢' if bias == 'LONG' else '🔴'} <b>{bias}</b>\nBTC: <code>${price:,.2f}</code>\nConfidence: {confidence:.0%}\nPatterns: {patterns}\n<i>Awaiting minute {BOT_CONFIG.dynamic.execution_window_start} risk approval...</i>"
        )

    def scholar_review(self, trades_reviewed: int, win_rate: float, total_pnl: float, regime: str):
        self._dispatch(
            f"🎓 Scholar Review | {trades_reviewed} trades", 
            f"Win Rate: {win_rate:.0%}\nP&L: {'+' if total_pnl >= 0 else ''}${abs(total_pnl):,.2f}\nRegime: {regime}\nParameters may have been adjusted.", 
            self.SOUND_TRADE, 
            f"🎓 <b>Scholar Meta-Review</b>\nReviewed {trades_reviewed} trades.\n\nWin Rate: {win_rate:.0%}\nP&L: {'+' if total_pnl >= 0 else ''}${total_pnl:,.2f}\nMarket Regime: {regime.capitalize()}\n<i>Check dashboard for parameter adjustments.</i>"
        )

    def kill_switch(self, activated: bool):
        if activated:
            self._dispatch(
                "🛑 Kill Switch Activated", 
                "All trading halted immediately.\nNo new positions will be opened.", 
                self.SOUND_URGENT, 
                "🛑 <b>KILL SWITCH ACTIVATED</b>\nAll trading halted. No new positions will be opened."
            )
        else:
            self._dispatch(
                "✅ Kill Switch Deactivated", 
                "Trading operations resumed.", 
                self.SOUND_TRADE, 
                "▶️ <b>Kill Switch Deactivated</b>\nTrading operations resumed."
            )

    def alert(self, title: str, message: str, urgent: bool = False):
        self._dispatch(
            title, 
            message, 
            self.SOUND_URGENT if urgent else self.SOUND_LOSS, 
            f"{'🚨' if urgent else '⚠️'} <b>{title}</b>\n{message}"
        )

    def test(self):
        print("\n" + "="*50 + "\n[Notifier] 🧪 RUNNING NOTIFICATION TEST...")
        if not self.tg_enabled:
            print("[Notifier] ❌ TELEGRAM SKIPPED: Missing keys in .env")
        else:
            print(f"[Notifier] 🟢 Telegram Enabled. Chat ID: {self.tg_chat_id}...")
            
        if not self.toast_enabled:
            print("[Notifier] ❌ DESKTOP TOASTS SKIPPED.")
        else:
            print(f"[Notifier] 🟢 Desktop Toasts Enabled.")
            
        self._run_dispatch(
            "Trading Bot — Notifications Active", 
            "Toast notifications are working.\nYou will be notified on trade events.", 
            self.SOUND_TRADE, 
            "✅ <b>Bot Notifier Active</b>\nTelegram | Desktop notifications working perfectly."
        )
        print("="*50 + "\n")

    def _dispatch(self, t_title: str, t_body: str, sound: str, tg_msg: str):
        if self.enabled:
            threading.Thread(
                target=self._run_dispatch, 
                args=(t_title, t_body, sound, tg_msg), 
                daemon=True
            ).start()

    def _run_dispatch(self, t_title: str, t_body: str, sound: str, tg_msg: str):
        if self.tg_enabled:
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{self.tg_token}/sendMessage", 
                    json={
                        "chat_id": self.tg_chat_id, 
                        "text": tg_msg, 
                        "parse_mode": "HTML", 
                        "disable_web_page_preview": True
                    }, 
                    timeout=10
                )
                if r.status_code != 200:
                    log.error(f"[Notifier] Telegram Rejected: {r.text}")
            except Exception as e:
                log.error(f"[Notifier] Telegram network exception: {e}")
                
        if self.toast_enabled:
            try:
                self._send_toast(t_title, t_body, sound)
                if sound != self.SOUND_SILENT:
                    self._play_backup_sound(sound)
            except Exception as e:
                log.warning(f"[Notifier] Desktop Toast dispatch failed: {e}")

    def _send_toast(self, title: str, body: str, sound: str):
        title_safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
        body_safe = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
        
        if sound == self.SOUND_SILENT:
            audio_tag = '<audio silent="true"/>'
            duration = "short"
        elif "Looping" in sound:
            audio_tag = f'<audio src="{sound}" loop="true"/>'
            duration = "long"
        else:
            audio_tag = f'<audio src="{sound}"/>'
            duration = "short"
            
        ps_script = f"""
        try {{[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
          $t = @'
          <toast duration="{duration}">
            <visual><binding template="ToastGeneric"><text>{title_safe}</text><text>{body_safe}</text></binding></visual>
            {audio_tag}
          </toast>
'@
          $x = New-Object Windows.Data.Xml.Dom.XmlDocument
          $x.LoadXml($t)
          $n = [Windows.UI.Notifications.ToastNotification]::new($x)
          $appId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
          [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($n)
        }} catch {{ }}
        """
        
        encoded = base64.b64encode(ps_script.encode("utf-16-le")).decode("ascii")
        kwargs = {"capture_output": True, "text": True, "timeout": 15}
        
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            kwargs["startupinfo"] = si
            
        subprocess.run([self._ps, "-NoProfile", "-EncodedCommand", encoded], **kwargs)

    def _play_backup_sound(self, sound: str):
        try:
            if sys.platform == "win32":
                import winsound
                if sound == self.SOUND_URGENT:
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                elif sound == self.SOUND_LOSS:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                elif sound in (self.SOUND_WIN, self.SOUND_TRADE, self.SOUND_SIGNAL):
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                else:
                    winsound.MessageBeep(winsound.MB_OK)
            elif self._is_wsl and self._ps:
                freq = {
                    self.SOUND_URGENT: 1000, 
                    self.SOUND_LOSS: 600, 
                    self.SOUND_WIN: 800, 
                    self.SOUND_TRADE: 850, 
                    self.SOUND_SIGNAL: 750
                }.get(sound, 750)
                subprocess.run([self._ps, "-NoProfile", "-Command", f"[Console]::Beep({freq}, 300)"], 
                    capture_output=True, 
                    timeout=5
                )
        except Exception:
            pass

    def _detect_environment(self):
        try:
            with open("/proc/version", "r", encoding="utf-8") as f:
                content = f.read().lower()
                self._is_wsl = "microsoft" in content or "wsl" in content
        except Exception:
            self._is_wsl = False

    def _find_powershell(self) -> Optional[str]:
        if self._is_wsl:
            candidates =[
                "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", 
                "/mnt/c/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe", 
                "powershell.exe"
            ]
        else:
            candidates =[
                os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"), 
                "powershell.exe"
            ]
            
        for p in candidates:
            try:
                if subprocess.run([p, "-NoProfile", "-Command", "Write-Output ok"], capture_output=True, text=True, timeout=10).returncode == 0:
                    return p
            except Exception:
                continue
        return None
