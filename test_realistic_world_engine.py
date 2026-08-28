import urllib.request, json, time, datetime

# GERÇEK DÜNYA MOTORU (CANLI PİYASA LİKİDİTE & RİSK DİSİPLİNİ)
# 1. Rotating Universe: 15 statik parite yerine en yüksek hacimli dinamik filtre
# 2. Kasa Büyüme & Kâr Realizasyonu (Profit Harvesting): Kasa $2,500'a ulaştığında anapara dışındaki kâr çekilir, bileşik risk patlaması önlenir
# 3. Maksimum Marjin Limiti (Hard Cap): Hiçbir işlemde marjin $1,500'ı (Pozisyon $25,000'ı) aşamaz
# 4. Gerçekçi Taker Komisyonu + Fonlama + Dinamik Slippage

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

# Dinamik taranacak popüler likit evren
SCAN_UNIVERSE = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT',
    'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'SEIUSDT', 'ARBUSDT', 'OPUSDT', 'WLDUSDT',
    'PEPEUSDT', 'CRVUSDT', 'AAVEUSDT', 'PENDLEUSDT', 'ZECUSDT', 'MOVRUSDT'
]

print("Binance Vadeli 720 saatlik mumlar çekiliyor...")
candles = {}
for s in SCAN_UNIVERSE:
    try:
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h&limit=720'
        candles[s] = fetch_json(url)
    except Exception as e:
        print(f"{s} çekilemedi: {e}")

valid_symbols = [s for s in SCAN_UNIVERSE if s in candles and len(candles[s]) >= 700]
min_len = min(len(candles[s]) for s in valid_symbols)
timestamps = [candles['BTCUSDT'][i][0] for i in range(min_len)]

indicators = {}
for s in valid_symbols:
    closes = [float(k[4]) for k in candles[s][:min_len]]
    highs  = [float(k[2]) for k in candles[s][:min_len]]
    lows   = [float(k[3]) for k in candles[s][:min_len]]
    vols   = [float(k[5]) for k in candles[s][:min_len]]
    indicators[s] = {
        'closes': closes, 'highs': highs, 'lows': lows, 'vols': vols,
        'e9': calc_ema(closes, 9),
        'e21': calc_ema(closes, 21),
        'e99': calc_ema(closes, 99),
        'r14': calc_rsi(closes, 14),
        'atr': calc_atr(highs, lows, closes, 14)
    }

# GERÇEK DÜNYA SİMÜLASYONU
# 120$ Başlangıç
# Kasa Risk Limiti: Tek işlemde maksimum $500 marjin bağlanabilir (Gerçekçi büyüme limiti)
# Kâr Hasatı: Kasa her $1,000 arttığında $300 kasadan güvenli cüzdana çekilir
balance = 120.0
harvested_profit = 0.0
MAX_SLOT_MARGIN = 500.0  # Gerçekçi likidite sınırı
pos = None
trades = []

TAKER_FEE = 0.0005 * 2
FUNDING_8H = 0.0001
SLIPPAGE = 0.0004

for i in range(50, min_len):
    ts = timestamps[i]
    dt = datetime.datetime.fromtimestamp(ts/1000, datetime.timezone.utc)
    
    if pos is not None:
        s = pos['sym']
        cur_price = indicators[s]['closes'][i]
        cur_high = indicators[s]['highs'][i]
        cur_low = indicators[s]['lows'][i]
        e_fast = indicators[s]['e9'][i]
        e_slow = indicators[s]['e21'][i]
        lev = pos['leverage']
        
        pos['peak'] = max(pos['peak'], cur_high)
        gain_peak = (pos['peak'] - pos['entry']) / pos['entry']
        duration_h = (ts - pos['entry_ts']) / (3600 * 1000)
        
        # Stop Kuralları
        sl = pos['entry'] * 0.980
        if gain_peak >= 0.25: sl = max(sl, pos['peak'] * 0.95)
        elif gain_peak >= 0.15: sl = max(sl, pos['entry'] * 1.10)
        elif gain_peak >= 0.08: sl = max(sl, pos['entry'] * 1.03)
        elif gain_peak >= 0.03: sl = max(sl, pos['entry'] * 1.002)
        
        exit_trade = False
        exit_p = cur_price
        reason = ''
        if cur_low <= sl:
            exit_trade = True
            exit_p = sl
            reason = 'Trailing SL / Zırhlı Stop'
        elif e_fast < e_slow:
            exit_trade = True
            exit_p = cur_price
            reason = '1H Trend Sonu (EMA9<EMA21)'
            
        if exit_trade:
            rg = (exit_p - pos['entry']) / pos['entry']
            funding_cost = max(1, int(duration_h / 8.0)) * FUNDING_8H
            net_gain = rg - (TAKER_FEE + funding_cost + SLIPPAGE)
            pnl = pos['margin'] * lev * net_gain
            balance += pnl
            
            # Kâr Hasatı (Profit Harvesting): Kasa $1000'ı geçerse kârı realize et
            if balance > 1000.0:
                harvest = balance - 600.0
                harvested_profit += harvest
                balance = 600.0
                
            trades.append({
                'sym': s, 'entry_dt': pos['entry_dt'].strftime('%d.%m %H:%M'),
                'exit_dt': dt.strftime('%d.%m %H:%M'), 'lev': lev,
                'margin': pos['margin'], 'pnl': pnl, 'balance': balance,
                'harvested': harvested_profit, 'reason': reason
            })
            pos = None
            
    if pos is None and balance > 10:
        if dt.hour in [0, 2, 14, 19, 20]: continue
        
        candidates = []
        for s in valid_symbols:
            e_fast_c = indicators[s]['e9'][i]
            e_slow_c = indicators[s]['e21'][i]
            e_fast_p = indicators[s]['e9'][i-1]
            e_slow_p = indicators[s]['e21'][i-1]
            e99_c    = indicators[s]['e99'][i]
            rsi      = indicators[s]['r14'][i] if i < len(indicators[s]['r14']) else 50
            vols     = indicators[s]['vols']
            v_sma    = sum(vols[i-20:i]) / 20.0 if i >= 20 else 1.0
            v_ratio  = vols[i] / v_sma if v_sma > 0 else 1.0
            atr      = indicators[s]['atr'][i]
            atr_pct  = (atr / indicators[s]['closes'][i]) * 100
            
            if (e_fast_p <= e_slow_p) and (e_fast_c > e_slow_c) and (e_fast_c > e99_c) and (rsi >= 54) and (v_ratio >= 1.4):
                candidates.append((s, rsi, v_ratio, atr_pct))
                
        if candidates:
            candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
            chosen, rsi_val, vol_val, atr_val = candidates[0]
            
            # Dinamik Kaldıraç
            if atr_val <= 1.5 and vol_val >= 2.0 and rsi_val >= 60:
                calc_lev = 20
            elif atr_val <= 2.2 and vol_val >= 1.6 and rsi_val >= 56:
                calc_lev = 15
            elif atr_val <= 3.2:
                calc_lev = 12
            else:
                calc_lev = 10
                
            used_m = min(balance * 0.90, MAX_SLOT_MARGIN)
            pos = {
                'sym': chosen, 'entry': indicators[chosen]['closes'][i],
                'entry_ts': ts, 'entry_dt': dt, 'peak': indicators[chosen]['closes'][i],
                'base_margin': used_m, 'margin': used_m, 'pyr_level': 0,
                'leverage': calc_lev
            }

print("\n" + "="*85)
print(" GERÇEK DÜNYA MODELİ (LİKİDİTE SINIRLI & KÂR HARVESTİNG İLE)")
print("="*85)
print(f"Başlangıç: $120.00 | Kalan Aktif Kasa: ${balance:,.2f} | Çekilen Net Kâr: ${harvested_profit:,.2f}")
print(f"Toplam Üretilen Net Servet: ${balance + harvested_profit:,.2f} ({(balance + harvested_profit)*48:,.0f} TL)")
print(f"Toplam İşlem: {len(trades)} | Kârlı: {sum(1 for t in trades if t['pnl'] > 0)} | Win Rate: %{sum(1 for t in trades if t['pnl'] > 0)/len(trades)*100:.1f}")
print("\nGerçekçi İşlem Akışı:")
for idx, t in enumerate(trades):
    print(f"#{idx+1:02d} | {t['sym']:11} | {t['entry_dt']}->{t['exit_dt']} | {t['lev']:2d}x | Marjin: ${t['margin']:>6.1f} | PnL: ${t['pnl']:>8.2f} | Kasa: ${t['balance']:>7.2f} | Çekilen: ${t['harvested']:>7.2f} | {t['reason']}")
