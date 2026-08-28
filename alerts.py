import urllib.request, urllib.parse, json, time, logging
from typing import Optional, Dict, Any

logger = logging.getLogger("alerts")

class TelegramAlertManager:
    """
    Production-grade Telegram Alert Manager:
    - Rate limit & Exponential Backoff Retry (handles 429 & network timeouts)
    - Standalone formatted message templates
    - Safe execution (never crashes engine if Telegram is down)
    """
    def __init__(self, token: str = "", chat_id: str = "", enabled: bool = True):
        self.token = token.strip()
        self.chat_id = str(chat_id).strip()
        self.enabled = enabled and bool(self.token and self.chat_id)
        self.last_sent_ts = 0.0
        self.min_interval = 1.0 # Max 1 message per second rate limit

    def send_message(self, text: str, parse_mode: str = "HTML", max_retries: int = 3) -> bool:
        if not self.enabled:
            return False

        # Local rate limiter
        now = time.time()
        if now - self.last_sent_ts < self.min_interval:
            time.sleep(self.min_interval - (now - self.last_sent_ts))

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(
                    url, data=payload, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    if resp.status == 200:
                        self.last_sent_ts = time.time()
                        return True
            except urllib.error.HTTPError as e:
                if e.code == 429: # Rate limit by Telegram
                    wait_sec = attempt * 2.0
                    time.sleep(wait_sec)
                else:
                    logger.warning(f"Telegram HTTP Error {e.code}: {e.reason}")
                    break
            except Exception as e:
                logger.warning(f"Telegram network error (attempt {attempt}): {e}")
                time.sleep(attempt * 1.5)

        return False

    # Standardized Message Templates
    def format_entry_signal(self, sym: str, price: float, lev: int, margin: float, notional: float, sl: float, atr_pct: float) -> str:
        return (
            f"🚀 <b>YENİ POZİSYON AÇILDI: #{sym}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 <b>Yön:</b> LONG (Alış)\n"
            f"💵 <b>Giriş Fiyatı:</b> <code>{price:.5f}$</code>\n"
            f"⚡ <b>Kaldıraç:</b> <code>{lev}x (Dinamik)</code>\n"
            f"💰 <b>Marjin:</b> <code>${margin:,.2f}</code>\n"
            f"📊 <b>Pozisyon Büyüklüğü:</b> <code>${notional:,.2f}</code>\n"
            f"🛡️ <b>Zırhlı Stop (SL):</b> <code>{sl:.5f}$ (%2.0)</code>\n"
            f"📈 <b>ATR Volatilite:</b> <code>%{atr_pct:.2f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <i>Zaman: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</i>"
        )

    def format_pyramid_event(self, sym: str, level: int, add_margin: float, total_margin: float, current_pnl_usd: float) -> str:
        return (
            f"🔥 <b>PİRAMİT KADEMESİ TETİKLENDİ (#{sym})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔺 <b>Kademe:</b> {level}. Ekleme (+%25 Marjin)\n"
            f"💵 <b>Eklenen Tutar:</b> <code>+${add_margin:,.2f}</code>\n"
            f"💼 <b>Toplam Marjin:</b> <code>${total_margin:,.2f}</code>\n"
            f"📈 <b>Anlık Kâr:</b> <code>+${current_pnl_usd:,.2f}</code>\n"
            f"🛡️ <b>Stop Durumu:</b> Kâr Kilitleme / Başabaş Aktif\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    def format_close_signal(self, sym: str, exit_p: float, pnl_usd: float, pnl_pct: float, new_bal: float, reason: str) -> str:
        icon = "🎉" if pnl_usd >= 0 else "🛑"
        color_pnl = f"+${pnl_usd:,.2f}" if pnl_usd >= 0 else f"-${abs(pnl_usd):,.2f}"
        return (
            f"{icon} <b>POZİSYON KAPATILDI: #{sym}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🚪 <b>Çıkış Fiyatı:</b> <code>{exit_p:.5f}$</code>\n"
            f"📊 <b>İşlem PnL:</b> <code>{color_pnl} (%{pnl_pct:+.2f})</code>\n"
            f"🎯 <b>Çıkış Nedeni:</b> {reason}\n"
            f"💼 <b>Yeni Net Kasa:</b> <code>${new_bal:,.2f} ({new_bal*48:,.0f} TL)</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <i>Zaman: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</i>"
        )

    def format_circuit_breaker(self, daily_loss_pct: float, cur_bal: float, cooldown_hours: int) -> str:
        return (
            f"🚨🚨 <b>DEVRE KESİCİ (CIRCUIT BREAKER) AKTİF</b> 🚨🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Günlük Kayıp:</b> <code>-%{abs(daily_loss_pct):.2f}</code>\n"
            f"🛑 <b>Mevcut Kasa:</b> <code>${cur_bal:,.2f}</code>\n"
            f"🔒 <b>Aksiyon:</b> Yeni işlem açma {cooldown_hours} saatliğine durduruldu.\n"
            f"🛡️ <i>Sermaye koruma protokolü devreye girdi.</i>"
        )
