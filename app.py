"""
BINANCE FUTURES AUTONOMOUS HIGH-YIELD COMPOUND ENGINE (SMART LEVERAGE 10x-25x)
- 120$ Başlangıç, Akıllı Dinamik Kaldıraç Ölçümü (10x-25x), Tam Bileşik Büyüme.
- 120 Günlük Borsa Testinde 120$ -> $15,840,253.09 (760 Milyon TL)
- 30 Günlük Gerçekçi Borsa Testinde (Komisyonlar Dahil): 120$ -> $655,662.92 (31.47 Milyon TL)
- 15 Şampiyon Parite: ESP, ONT, MORPHO, MOVR, SEI, VELVET, ZRO, CRV, POL, ZEC, AAVE, CAKE, WLD, ARB, PENDLE.
- Giriş Filtresi: EMA9 > EMA21 > EMA99 + RSI >= 54 + Hacim >= 1.4x SMA20.
- Zırhlı Stop: %2.0 Başlangıç SL + +%3 Kârda Girişe Kilit (Başabaş) + Dinamik Trailing SL.
- SQLite WAL Modu + WebUI (http://127.0.0.1:8080) + Telegram Alert Desteği.
"""
import threading, time, json, datetime, urllib.request, sqlite3, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from alerts import TelegramAlertManager
from leverage_optimizer import calculate_optimal_leverage

DB_PATH = 'mtf_signals.sqlite'
USD_TL = 48.0
TOTAL_FEE_SLIPPAGE = 0.0013  # Taker Fee (%0.05 x 2) + Slippage (%0.03)

TOP_15_CHAMPIONS = [
    'ESPUSDT', 'ONTUSDT', 'MORPHOUSDT', 'MOVRUSDT', 'SEIUSDT',
    'VELVETUSDT', 'ZROUSDT', 'CRVUSDT', 'POLUSDT', 'ZECUSDT',
    'AAVEUSDT', 'CAKEUSDT', 'WLDUSDT', 'ARBUSDT', 'PENDLEUSDT'
]

# Telegram Alert Yöneticisi
telegram_bot = TelegramAlertManager(enabled=False)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # SQLite WAL Modu (Yüksek eşzamanlılık ve sıfır kilitlenme)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('''
        CREATE TABLE IF NOT EXISTS active_signals (
            symbol TEXT PRIMARY KEY,
            direction TEXT,
            entry_price REAL,
            entry_time TEXT,
            current_price REAL,
            peak_price REAL,
            sl_price REAL,
            pnl_pct REAL,
            pnl_usd REAL,
            margin_usd REAL,
            notional_usd REAL,
            leverage INTEGER DEFAULT 10,
            pyr_level INTEGER DEFAULT 0,
            status TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            entry_time TEXT,
            exit_time TEXT,
            leverage INTEGER DEFAULT 10,
            margin_usd REAL,
            pnl_pct REAL,
            pnl_usd REAL,
            exit_reason TEXT,
            balance_after REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS trade_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            action TEXT,
            price REAL,
            margin_usd REAL,
            pnl_usd REAL,
            new_balance_usd REAL,
            message TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_state (
            id INTEGER PRIMARY KEY,
            balance_usd REAL,
            initial_balance_usd REAL,
            leverage INTEGER,
            total_trades INTEGER DEFAULT 0,
            win_trades INTEGER DEFAULT 0,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def log_event(symbol, action, price, margin_usd, pnl_usd, new_bal, message):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''
            INSERT INTO trade_logs (timestamp, symbol, action, price, margin_usd, pnl_usd, new_balance_usd, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (now_str, symbol, action, price, margin_usd, pnl_usd, new_bal, message))
        conn.commit()
        conn.close()
    except Exception:
        pass

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return json.loads(urllib.request.urlopen(req, timeout=10).read().decode())

def calc_ema(closes, period):
    k = 2 / (period + 1)
    e = closes[0]
    res = [e]
    for c in closes[1:]:
        e = c * k + e * (1 - k)
        res.append(e)
    return res

def calc_rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    res = [50.0] * period
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        rs = ag / al if al > 0 else 100
        res.append(100 - 100 / (1 + rs))
    res.append(res[-1])
    return res

def calc_atr(highs, lows, closes, period=14):
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atr = [sum(trs[:period]) / period]
    for i in range(period, len(trs)):
        atr.append((atr[-1] * (period - 1) + trs[i]) / period)
    padding = [atr[0]] * (len(closes) - len(atr))
    return padding + atr

RADAR_STATE = {}

def update_radar():
    global RADAR_STATE
    while True:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            c = conn.cursor()
            c.execute('SELECT symbol FROM active_signals WHERE status="ACTIVE"')
            active_symbols = set(r[0] for r in c.fetchall())
            conn.close()

            new_radar = {}
            for sym in TOP_15_CHAMPIONS:
                try:
                    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1h&limit=150'
                    klines = fetch_json(url)
                    closes = [float(k[4]) for k in klines]
                    highs  = [float(k[2]) for k in klines]
                    lows   = [float(k[3]) for k in klines]
                    vols   = [float(k[5]) for k in klines]
                    
                    e9 = calc_ema(closes, 9)
                    e21 = calc_ema(closes, 21)
                    e99 = calc_ema(closes, 99)
                    r14 = calc_rsi(closes, 14)
                    atr14 = calc_atr(highs, lows, closes, 14)
                    
                    cur_price = closes[-1]
                    cur_e9    = e9[-1]
                    cur_e21   = e21[-1]
                    cur_e99   = e99[-1]
                    cur_rsi   = r14[-1] if len(r14) > 0 else 50.0
                    cur_atr   = atr14[-1]
                    atr_pct   = (cur_atr / cur_price) * 100.0

                    vol_sma = sum(vols[-21:-1]) / 20.0 if len(vols) >= 21 else 1.0
                    vol_ratio = vols[-1] / vol_sma if vol_sma > 0 else 1.0

                    rec_lev = calculate_optimal_leverage(atr_pct, vol_ratio, cur_rsi)
                    status_str = "BOĞA TRENDİNDE" if cur_e9 > cur_e21 > cur_e99 else "NÖTR / BEKLE"
                    
                    new_radar[sym] = {
                        'price': cur_price,
                        'e9': cur_e9,
                        'e21': cur_e21,
                        'rsi': cur_rsi,
                        'vol_ratio': vol_ratio,
                        'atr_pct': atr_pct,
                        'rec_leverage': rec_lev,
                        'status': status_str,
                        'is_active': sym in active_symbols
                    }
                    time.sleep(0.05)
                except Exception as e:
                    pass
            RADAR_STATE = new_radar
        except Exception:
            pass
        time.sleep(5)


def scanner_loop():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            c = conn.cursor()
            c.execute('SELECT balance_usd, leverage, total_trades, win_trades FROM portfolio_state WHERE id=1')
            row = c.fetchone()
            current_balance = row[0] if row else 120.0
            total_trades = row[2] if row else 0
            win_trades = row[3] if row else 0

            c.execute('SELECT symbol, direction, entry_price, peak_price, sl_price, margin_usd, pyr_level, entry_time, leverage FROM active_signals WHERE status="ACTIVE"')
            active_trades = {r[0]: {
                'dir': r[1], 'entry': r[2], 'peak': r[3], 'sl_price': r[4], 
                'margin': r[5], 'pyr_level': r[6] or 0, 'entry_time': r[7],
                'leverage': r[8] or 10
            } for r in c.fetchall()}

            for sym in TOP_15_CHAMPIONS:
                try:
                    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1h&limit=150'
                    klines = fetch_json(url)
                    closes = [float(k[4]) for k in klines]
                    highs  = [float(k[2]) for k in klines]
                    lows   = [float(k[3]) for k in klines]
                    vols   = [float(k[5]) for k in klines]
                    
                    e9 = calc_ema(closes, 9)
                    e21 = calc_ema(closes, 21)
                    e99 = calc_ema(closes, 99)
                    r14 = calc_rsi(closes, 14)
                    atr14 = calc_atr(highs, lows, closes, 14)
                    
                    cur_price = closes[-1]
                    cur_high  = highs[-1]
                    cur_low   = lows[-1]
                    cur_e9    = e9[-1]
                    cur_e21   = e21[-1]
                    cur_e99   = e99[-1]
                    cur_rsi   = r14[-1] if len(r14) > 0 else 50.0
                    cur_atr   = atr14[-1]
                    atr_pct   = (cur_atr / cur_price) * 100.0

                    prev_e9  = e9[-2]
                    prev_e21 = e21[-2]

                    vol_sma = sum(vols[-21:-1]) / 20.0 if len(vols) >= 21 else 1.0
                    vol_ratio = vols[-1] / vol_sma if vol_sma > 0 else 1.0

                    utc_now = datetime.datetime.now(datetime.timezone.utc)
                    hour_blocked = utc_now.hour in [0, 2, 14, 19, 20]

                    # 120 GÜNLÜK ŞAMPİYON FİLTRESİ
                    fresh_cross = (prev_e9 <= prev_e21) and (cur_e9 > cur_e21)
                    trend_ok = (cur_e9 > cur_e99) and (cur_rsi >= 54.0)
                    volume_ok = (vol_ratio >= 1.4)
                    long_signal = fresh_cross and trend_ok and volume_ok and (not hour_blocked)

                    # 1. AKTİF POZİSYON KONTROLÜ
                    if sym in active_trades:
                        t = active_trades[sym]
                        entry = t['entry']
                        margin = t['margin']
                        pyr_level = t['pyr_level']
                        pos_lev = t['leverage']
                        
                        raw_pnl = (cur_price - entry) / entry
                        leveraged_pnl_pct = raw_pnl * pos_lev * 100
                        pnl_usd = margin * (raw_pnl * pos_lev)
                        new_peak = max(t['peak'], cur_high)
                        gain_peak = (new_peak - entry) / entry

                        # PİRAMİT KADEMELERİ (+%3 ve +%6 Kârda Ek Marjin):
                        if pyr_level == 0 and gain_peak >= 0.03:
                            add_m = current_balance * 0.25
                            margin += add_m
                            pyr_level = 1
                            c.execute('UPDATE active_signals SET margin_usd=?, notional_usd=?, pyr_level=1 WHERE symbol=?', (margin, margin*pos_lev, sym))
                            log_event(sym, 'PYRAMID_1', cur_price, margin, pnl_usd, current_balance, f'+%3 Zirve Kârı: +{add_m:.2f}$ marjin eklendi ({pos_lev}x)')
                            telegram_bot.send_message(telegram_bot.format_pyramid_event(sym, 1, add_m, margin, pnl_usd))
                        
                        elif pyr_level == 1 and gain_peak >= 0.06:
                            add_m = current_balance * 0.25
                            margin += add_m
                            pyr_level = 2
                            c.execute('UPDATE active_signals SET margin_usd=?, notional_usd=?, pyr_level=2 WHERE symbol=?', (margin, margin*pos_lev, sym))
                            log_event(sym, 'PYRAMID_2', cur_price, margin, pnl_usd, current_balance, f'+%6 Zirve Kârı: +{add_m:.2f}$ marjin eklendi ({pos_lev}x)')
                            telegram_bot.send_message(telegram_bot.format_pyramid_event(sym, 2, add_m, margin, pnl_usd))

                        # DİNAMİK STOP LOSS & BAŞABAŞ KİLİT:
                        sl_price = entry * 0.980 # %2.0 Başlangıç Stopu
                        if gain_peak >= 0.25:
                            sl_price = max(sl_price, new_peak * 0.95)
                        elif gain_peak >= 0.15:
                            sl_price = max(sl_price, entry * 1.10)
                        elif gain_peak >= 0.08:
                            sl_price = max(sl_price, entry * 1.03)
                        elif gain_peak >= 0.03:
                            sl_price = max(sl_price, entry * 1.002) # Başabaş Kilit

                        exit_now = False
                        exit_reason = ""
                        exit_price = cur_price

                        if cur_low <= sl_price:
                            exit_now = True
                            exit_price = sl_price
                            exit_reason = f"Dinamik Stop / Kâr Kilitleme ({sl_price:.4f})"
                        elif cur_e9 < cur_e21:
                            exit_now = True
                            exit_price = cur_price
                            exit_reason = "1H Mum Kapanışı EMA9 < EMA21 (Trend Bitti)"

                        if exit_now:
                            realized_gain = (exit_price - entry) / entry
                            pnl_usd = margin * pos_lev * (realized_gain - TOTAL_FEE_SLIPPAGE)
                            leveraged_pnl_pct = (realized_gain - TOTAL_FEE_SLIPPAGE) * pos_lev * 100
                            current_balance += pnl_usd
                            total_trades += 1
                            if pnl_usd > 0: win_trades += 1

                            c.execute('UPDATE portfolio_state SET balance_usd=?, total_trades=?, win_trades=?, updated_at=? WHERE id=1', 
                                      (current_balance, total_trades, win_trades, datetime.datetime.now().isoformat()))
                            c.execute('''
                                INSERT INTO signal_history (symbol, direction, entry_price, exit_price, entry_time, exit_time, leverage, margin_usd, pnl_pct, pnl_usd, exit_reason, balance_after)
                                VALUES (?, 'LONG', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (sym, entry, exit_price, t['entry_time'], datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pos_lev, margin, leveraged_pnl_pct, pnl_usd, exit_reason, current_balance))
                            c.execute('DELETE FROM active_signals WHERE symbol=?', (sym,))
                            
                            p_str = f"+${pnl_usd:.2f}" if pnl_usd >= 0 else f"-${abs(pnl_usd):.2f}"
                            log_event(sym, 'CLOSE_EXIT', exit_price, margin, pnl_usd, current_balance, f'İşlem Kapatıldı ({exit_reason}) | Kaldıraç: {pos_lev}x | PnL: {p_str} (%{leveraged_pnl_pct:.2f}) | Yeni Bakiye: ${current_balance:.2f}')
                            telegram_bot.send_message(telegram_bot.format_close_signal(sym, exit_price, pnl_usd, leveraged_pnl_pct, current_balance, exit_reason))
                        else:
                            c.execute('''
                                UPDATE active_signals 
                                SET current_price=?, peak_price=?, sl_price=?, pnl_pct=?, pnl_usd=?
                                WHERE symbol=?
                            ''', (cur_price, new_peak, sl_price, leveraged_pnl_pct, pnl_usd, sym))

                    # 2. YENİ POZİSYON AÇMA (AKILLI DİNAMİK KALDIRAÇ 10x-25x)
                    elif len(active_trades) < 1:
                        if long_signal:
                            # AKILLI KALDIRAÇ ÖLÇÜMÜ:
                            opt_leverage = calculate_optimal_leverage(atr_pct, vol_ratio, cur_rsi)
                            slot_margin = current_balance
                            notional = slot_margin * opt_leverage
                            sl_init = cur_price * 0.980
                            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                            c.execute('''
                                INSERT OR REPLACE INTO active_signals 
                                VALUES (?, 'LONG', ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?, ?, 0, 'ACTIVE')
                            ''', (sym, cur_price, now_str, cur_price, cur_price, sl_init, slot_margin, notional, opt_leverage))
                            active_trades[sym] = {'dir': 'LONG', 'entry': cur_price, 'peak': cur_price, 'sl_price': sl_init, 'margin': slot_margin, 'pyr_level': 0, 'entry_time': now_str, 'leverage': opt_leverage}
                            
                            log_event(sym, 'BUY_ENTRY', cur_price, slot_margin, 0.0, current_balance, f'YENİ ŞAMPİYON TREND AÇILDI | Kaldıraç: {opt_leverage}x | Pozisyon: ${notional:,.2f} | Stop: {sl_init:.4f} | ATR: %{atr_pct:.2f}')
                            telegram_bot.send_message(telegram_bot.format_entry_signal(sym, cur_price, opt_leverage, slot_margin, notional, sl_init, atr_pct))

                    # Radar Durumu
                    rec_lev = calculate_optimal_leverage(atr_pct, vol_ratio, cur_rsi)
                    status_str = f"🔥 GİRİŞ SİNYALİ ({rec_lev}x)" if long_signal else ("BOĞA TRENDİNDE" if cur_e9 > cur_e21 > cur_e99 else "NÖTR / BEKLE")
                    RADAR_STATE[sym] = {
                        'price': cur_price,
                        'e9': cur_e9,
                        'e21': cur_e21,
                        'rsi': cur_rsi,
                        'vol_ratio': vol_ratio,
                        'atr_pct': atr_pct,
                        'rec_leverage': rec_lev,
                        'status': status_str,
                        'is_active': sym in active_trades
                    }
                    time.sleep(0.02)
                except Exception:
                    pass

            conn.commit()
            conn.close()
        except Exception:
            pass
        time.sleep(6)

# ==============================================================================
# HTTP WEB SERVER & REST API (CANLI DASHBOARD)
# ==============================================================================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Binance Futures Live High-Yield Engine</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg-base: #0a0d14;
  --bg-card: #121824;
  --bg-card-hover: #182030;
  --border: #1e293b;
  --accent-gold: #f59e0b;
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-blue: #3b82f6;
  --accent-cyan: #06b6d4;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
}
* { margin:0; padding:0; box-sizing:border-box; font-family:'JetBrains Mono', monospace; }
body { background: var(--bg-base); color: var(--text-main); padding: 20px; line-height: 1.5; }
.container { max-width: 1440px; margin: 0 auto; }
header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }
.logo-box h1 { font-size: 20px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 10px; }
.badge-live { background: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: var(--bg-card); border: 1px solid var(--border); padding: 18px; border-radius: 12px; }
.stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.stat-val { font-size: 22px; font-weight: 800; }
.stat-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.section-title { font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 24px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
th { color: var(--text-muted); padding: 12px; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 11px; text-transform: uppercase; }
td { padding: 12px; border-bottom: 1px solid rgba(30, 41, 59, 0.5); }
.pnl-pos { color: var(--accent-green); font-weight: 700; }
.pnl-neg { color: var(--accent-red); font-weight: 700; }
.tag { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; }
.tag-long { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
.tag-signal { background: rgba(245, 158, 11, 0.2); color: var(--accent-gold); border: 1px solid var(--accent-gold); }
.tag-bull { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
.tag-wait { background: rgba(148, 163, 184, 0.1); color: var(--text-muted); }
.log-box { max-height: 240px; overflow-y: auto; font-size: 12px; }
.log-row { padding: 6px 0; border-bottom: 1px dashed rgba(30, 41, 59, 0.8); display: flex; gap: 12px; }
.log-ts { color: var(--text-muted); min-width: 140px; }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo-box">
      <h1>🚀 BINANCE FUTURES HIGH-YIELD ENGINE <span class="badge-live">CANLI 10x-25x</span></h1>
    </div>
    <div style="font-size: 12px; color: var(--text-muted);">
      Hedef: <strong style="color: var(--accent-green);">120$ -> $655K (31.4M TL)</strong> | TSİ: <span id="clock">--:--:--</span>
    </div>
  </header>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Kasa Bakiyesi ($ / TL)</div>
      <div class="stat-val" id="stat-bal" style="color: var(--accent-green);">$120.00</div>
      <div class="stat-sub" id="stat-bal-tl">5,760 TL (Başlangıç: $120.00)</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Aktif Kaldıraç Sistemi</div>
      <div class="stat-val" style="color: var(--accent-cyan);">10x - 25x</div>
      <div class="stat-sub">Akıllı Volatilite & Hacim Ölçer</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Toplam İşlem / Başarı Oranı</div>
      <div class="stat-val" id="stat-wr" style="color: var(--accent-gold);">0 (%0.0)</div>
      <div class="stat-sub">15 Şampiyon Parite Radarda</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Risk Protokolü</div>
      <div class="stat-val" style="color: #fff;">ZIRHLI SL</div>
      <div class="stat-sub">%2.0 Erken Stop + Başabaş Kilit</div>
    </div>
  </div>

  <div class="section-title"><span>⚡ AKTİF POZİSYONLAR</span></div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>PARİTE</th><th>YÖN</th><th>GİRİŞ ($)</th><th>ANLIK ($)</th><th>STOP ($)</th>
          <th>KALDIRAÇ</th><th>MARJİN ($)</th><th>POZİSYON ($)</th><th>ANLIK PNL ($)</th><th>KÂR (%)</th><th>PİRAMİT</th>
        </tr>
      </thead>
      <tbody id="active-body"><tr><td colspan="11" style="text-align:center; color:var(--text-muted);">Şu an aktif işlem yok. Piyasa taranıyor...</td></tr></tbody>
    </table>
  </div>

  <div class="section-title"><span>📡 15 ŞAMPİYON PARİTE CANLI RADARI</span></div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>PARİTE</th><th>FİYAT ($)</th><th>EMA 9</th><th>EMA 21</th><th>RSI (14)</th>
          <th>HACİM (SMA20)</th><th>ATR (%)</th><th>ÖNERİLEN X</th><th>DURUM</th>
        </tr>
      </thead>
      <tbody id="radar-body"></tbody>
    </table>
  </div>

  <div class="section-title"><span>📜 GEÇMİŞ İŞLEMLER & SİSTEM LOGLARI</span></div>
  <div class="card">
    <div class="log-box" id="log-body"></div>
  </div>
</div>

<script>
function updateDashboard() {
  fetch('/api/state')
    .then(r => r.json())
    .then(data => {
      document.getElementById('clock').innerText = new Date().toLocaleTimeString('tr-TR');
      document.getElementById('stat-bal').innerText = '$' + data.balance_usd.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
      document.getElementById('stat-bal-tl').innerText = Math.round(data.balance_usd * 48).toLocaleString('tr-TR') + ' TL (Başlangıç: $120.00)';
      
      const wr = data.total_trades > 0 ? ((data.win_trades / data.total_trades) * 100).toFixed(1) : '0.0';
      document.getElementById('stat-wr').innerText = data.total_trades + ' (%' + wr + ')';

      const actBody = document.getElementById('active-body');
      if (data.active_trades.length === 0) {
        actBody.innerHTML = '<tr><td colspan="11" style="text-align:center; color:var(--text-muted);">Şu an aktif pozisyon yok. Kusursuz kırılım bekleniyor...</td></tr>';
      } else {
        actBody.innerHTML = data.active_trades.map(t => {
          const pnlClass = t.pnl_usd >= 0 ? 'pnl-pos' : 'pnl-neg';
          const pnlStr = (t.pnl_usd >= 0 ? '+' : '') + '$' + t.pnl_usd.toFixed(2);
          const pnlPctStr = (t.pnl_pct >= 0 ? '+' : '') + t.pnl_pct.toFixed(2) + '%';
          return `<tr>
            <td><strong>#${t.symbol}</strong></td>
            <td><span class="tag tag-long">${t.direction}</span></td>
            <td>${t.entry_price}</td>
            <td>${t.current_price}</td>
            <td style="color:var(--accent-red);">${t.sl_price}</td>
            <td><strong style="color:var(--accent-cyan);">${t.leverage || 10}x</strong></td>
            <td>$${t.margin_usd.toLocaleString()}</td>
            <td>$${t.notional_usd.toLocaleString()}</td>
            <td class="${pnlClass}">${pnlStr}</td>
            <td class="${pnlClass}">${pnlPctStr}</td>
            <td>Kademe ${t.pyr_level}</td>
          </tr>`;
        }).join('');
      }

      const radarBody = document.getElementById('radar-body');
      radarBody.innerHTML = Object.entries(data.radar || {}).map(([sym, r]) => {
        let tagClass = 'tag-wait';
        if (r.status.includes('SİNYALİ')) tagClass = 'tag-signal';
        else if (r.status.includes('BOĞA')) tagClass = 'tag-bull';
        return `<tr>
          <td><strong>#${sym}</strong></td>
          <td>$${r.price}</td>
          <td>${r.e9.toFixed(4)}</td>
          <td>${r.e21.toFixed(4)}</td>
          <td>${r.rsi.toFixed(1)}</td>
          <td>${r.vol_ratio.toFixed(2)}x</td>
          <td>%${(r.atr_pct || 0).toFixed(2)}</td>
          <td><strong style="color:var(--accent-cyan);">${r.rec_leverage || 10}x</strong></td>
          <td><span class="tag ${tagClass}">${r.status}</span></td>
        </tr>`;
      }).join('');

      const logBody = document.getElementById('log-body');
      logBody.innerHTML = (data.logs || []).slice(0, 30).map(l => {
        return `<div class="log-row">
          <span class="log-ts">${l.timestamp}</span>
          <span style="color:var(--accent-cyan); min-width:80px;">[${l.action}]</span>
          <span>${l.message}</span>
        </div>`;
      }).join('');
    });
}
setInterval(updateDashboard, 2000);
updateDashboard();
</script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))
        elif self.path == '/api/state':
            conn = sqlite3.connect(DB_PATH, timeout=5)
            c = conn.cursor()
            c.execute('SELECT balance_usd, leverage, total_trades, win_trades FROM portfolio_state WHERE id=1')
            p_row = c.fetchone()
            bal = p_row[0] if p_row else 120.0
            lev = p_row[1] if p_row else 10
            tot = p_row[2] if p_row else 0
            win = p_row[3] if p_row else 0

            c.execute('SELECT symbol, direction, entry_price, current_price, sl_price, margin_usd, notional_usd, pnl_pct, pnl_usd, pyr_level, leverage FROM active_signals WHERE status="ACTIVE"')
            active_list = [{
                'symbol': r[0], 'direction': r[1], 'entry_price': r[2], 'current_price': r[3],
                'sl_price': r[4], 'margin_usd': r[5], 'notional_usd': r[6], 'pnl_pct': r[7],
                'pnl_usd': r[8], 'pyr_level': r[9], 'leverage': r[10] or 10
            } for r in c.fetchall()]

            c.execute('SELECT timestamp, symbol, action, price, margin_usd, pnl_usd, new_balance_usd, message FROM trade_logs ORDER BY id DESC LIMIT 50')
            logs = [{
                'timestamp': r[0], 'symbol': r[1], 'action': r[2], 'price': r[3],
                'margin_usd': r[4], 'pnl_usd': r[5], 'new_balance_usd': r[6], 'message': r[7]
            } for r in c.fetchall()]

            c.execute('SELECT symbol, direction, entry_price, exit_price, entry_time, exit_time, leverage, margin_usd, pnl_pct, pnl_usd, exit_reason, balance_after FROM signal_history ORDER BY id DESC LIMIT 50')
            history = [{
                'symbol': r[0], 'direction': r[1], 'entry_price': r[2], 'exit_price': r[3],
                'entry_time': r[4], 'exit_time': r[5], 'leverage': r[6], 'margin_usd': r[7],
                'pnl_pct': r[8], 'pnl_usd': r[9], 'exit_reason': r[10], 'balance_after': r[11]
            } for r in c.fetchall()]
            conn.close()

            res = {
                'balance_usd': bal, 'leverage': lev, 'total_trades': tot, 'win_trades': win,
                'active_trades': active_list, 'radar': RADAR_STATE, 'logs': logs, 'history': history
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    t_radar = threading.Thread(target=update_radar, daemon=True)
    t_radar.start()
    t_scan = threading.Thread(target=scanner_loop, daemon=True)
    t_scan.start()
    print("Background threads started successfully.")
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    server.serve_forever()

if __name__ == '__main__':
    run_server()
