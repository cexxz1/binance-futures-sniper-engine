import urllib.request, json, datetime

TOP_15_120D = [
    'ESPUSDT', 'ONTUSDT', 'MORPHOUSDT', 'MOVRUSDT', 'SEIUSDT',
    'VELVETUSDT', 'ZROUSDT', 'CRVUSDT', 'POLUSDT', 'ZECUSDT',
    'AAVEUSDT', 'CAKEUSDT', 'WLDUSDT', 'ARBUSDT', 'PENDLEUSDT'
]

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

all_candles = {}
for s in TOP_15_120D:
    k2 = fetch_json(f'https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h&limit=1440')
    first_ts = k2[0][0]
    k1 = fetch_json(f'https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h&limit=1440&endTime={first_ts - 1}')
    all_candles[s] = k1 + k2

min_len = min(len(all_candles[s]) for s in TOP_15_120D)
timestamps = [all_candles['MORPHOUSDT'][i][0] for i in range(min_len)]

indicators = {}
for s in TOP_15_120D:
    closes = [float(k[4]) for k in all_candles[s][:min_len]]
    highs  = [float(k[2]) for k in all_candles[s][:min_len]]
    lows   = [float(k[3]) for k in all_candles[s][:min_len]]
    vols   = [float(k[5]) for k in all_candles[s][:min_len]]
    indicators[s] = {
        'closes': closes, 'highs': highs, 'lows': lows, 'vols': vols,
        'e9': calc_ema(closes, 9),
        'e21': calc_ema(closes, 21),
        'e99': calc_ema(closes, 99),
        'r14': calc_rsi(closes, 14),
        'atr': calc_atr(highs, lows, closes, 14)
    }

# Simülasyon Test Fonksiyonu
def simulate(sl_mode='fixed_2pct', lev_mode='fixed_10x'):
    balance = 120.0
    pos = None
    trades = []
    liquidated = False
    
    for i in range(100, min_len):
        ts = timestamps[i]
        dt = datetime.datetime.fromtimestamp(ts/1000, datetime.timezone.utc)
        
        if pos is not None:
            s = pos['sym']
            cur_price = indicators[s]['closes'][i]
            cur_high = indicators[s]['highs'][i]
            cur_low = indicators[s]['lows'][i]
            e9 = indicators[s]['e9'][i]
            e21 = indicators[s]['e21'][i]
            lev = pos['leverage']
            
            # Isolated Liq Price
            mmr = 0.005 if lev <= 20 else (0.01 if lev <= 50 else 0.02)
            liq_price = pos['entry'] * (1 - (1 / lev) + mmr)
            if cur_low <= liq_price:
                balance = 0.0
                liquidated = True
                break
                
            pos['peak'] = max(pos['peak'], cur_high)
            gain_peak = (pos['peak'] - pos['entry']) / pos['entry']
            
            # Piramit (+%3 ve +%6 zirvede +%25 marjin)
            if pos['pyr_level'] == 0 and gain_peak >= 0.03:
                pos['margin'] += pos['base_margin'] * 0.25
                pos['pyr_level'] = 1
            elif pos['pyr_level'] == 1 and gain_peak >= 0.06:
                pos['margin'] += pos['base_margin'] * 0.25
                pos['pyr_level'] = 2
                
            # STOP LOSS MODELİ
            if sl_mode == 'no_sl':
                sl = 0 # Sadece EMA9 < EMA21 çıkışı
            elif sl_mode == 'fixed_2pct':
                sl = pos['entry'] * 0.980
                if gain_peak >= 0.25: sl = max(sl, pos['peak'] * 0.95)
                elif gain_peak >= 0.15: sl = max(sl, pos['entry'] * 1.10)
                elif gain_peak >= 0.08: sl = max(sl, pos['entry'] * 1.03)
                elif gain_peak >= 0.03: sl = max(sl, pos['entry'] * 1.002)
            elif sl_mode == 'fixed_3pct':
                sl = pos['entry'] * 0.970
                if gain_peak >= 0.25: sl = max(sl, pos['peak'] * 0.95)
                elif gain_peak >= 0.15: sl = max(sl, pos['entry'] * 1.10)
                elif gain_peak >= 0.08: sl = max(sl, pos['entry'] * 1.03)
                elif gain_peak >= 0.03: sl = max(sl, pos['entry'] * 1.002)
            elif sl_mode == 'atr_dynamic':
                # ATR(14) x 1.8 stop distance
                atr_val = indicators[s]['atr'][pos['entry_idx']]
                sl = pos['entry'] - (1.8 * atr_val)
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
                reason = 'SL'
            elif e9 < e21:
                exit_trade = True
                exit_p = cur_price
                reason = 'EMA'
                
            if exit_trade:
                rg = (exit_p - pos['entry']) / pos['entry']
                pnl = pos['margin'] * lev * (rg - 0.001)
                balance += pnl
                trades.append({'pnl': pnl, 'balance': balance, 'win': pnl > 0})
                pos = None
                
        if pos is None and balance > 5:
            if dt.hour in [0, 2, 14, 19, 20]: continue
            candidates = []
            for s in TOP_15_120D:
                e9_c = indicators[s]['e9'][i]
                e21_c = indicators[s]['e21'][i]
                e9_p = indicators[s]['e9'][i-1]
                e21_p = indicators[s]['e21'][i-1]
                e99_c = indicators[s]['e99'][i]
                rsi = indicators[s]['r14'][i] if i < len(indicators[s]['r14']) else 50
                vols = indicators[s]['vols']
                v_sma = sum(vols[i-20:i]) / 20.0 if i >= 20 else 1.0
                v_ratio = vols[i] / v_sma if v_sma > 0 else 1.0
                atr = indicators[s]['atr'][i]
                atr_pct = (atr / indicators[s]['closes'][i]) * 100
                
                if (e9_p <= e21_p) and (e9_c > e21_c) and (e9_c > e99_c) and (rsi >= 54) and (v_ratio >= 1.4):
                    candidates.append((s, rsi, v_ratio, atr_pct))
                    
            if candidates:
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                chosen, rsi_val, vol_val, atr_val = candidates[0]
                
                # KALDIRAÇ ÖLÇÜM MODLARI
                if lev_mode == 'fixed_10x':
                    calc_lev = 10
                elif lev_mode == 'volatility_optimal': # Matematiksel Optimal (Risk / ATR)
                    # Formül: Kaldıraç = Hedef Risk / ATR Yüzdesi (Min 10x, Max 25x)
                    # Eğer ATR %1.2 ise 25x, ATR %3.0 ise 10x
                    raw_lev = int(30.0 / max(atr_val, 1.0))
                    calc_lev = max(10, min(25, raw_lev))
                elif lev_mode == 'smart_momentum': # Volatilite + Hacim + RSI Ağırlıklı
                    if atr_val <= 1.5 and vol_val >= 2.0 and rsi_val >= 60:
                        calc_lev = 25
                    elif atr_val <= 2.2 and vol_val >= 1.6:
                        calc_lev = 18
                    elif atr_val <= 3.2:
                        calc_lev = 14
                    else:
                        calc_lev = 10
                        
                pos = {
                    'sym': chosen, 'entry': indicators[chosen]['closes'][i],
                    'entry_ts': ts, 'entry_dt': dt, 'entry_idx': i,
                    'peak': indicators[chosen]['closes'][i],
                    'base_margin': balance, 'margin': balance, 'pyr_level': 0,
                    'leverage': calc_lev
                }
                
    wins = sum(1 for t in trades if t['win'])
    total = len(trades)
    wr = (wins / total * 100) if total > 0 else 0
    return balance, total, wr, liquidated

print("==========================================================================================")
print(" 1. STOP LOSS KARŞILAŞTIRMASI (ATR SL KÂRI DÜŞÜRDÜ MÜ ARTIRDI MI?)")
print("==========================================================================================")
for sl_name in ['no_sl', 'fixed_2pct', 'fixed_3pct', 'atr_dynamic']:
    bal, cnt, wr, liq = simulate(sl_mode=sl_name, lev_mode='fixed_10x')
    liq_str = "LİKİT OLDU!" if liq else "Sıfır Likit"
    print(f"SL Modu: {sl_name:15} | 10x 120G Bakiye: ${bal:>14,.2f} ({bal*48:,.0f} TL) | İşlem: {cnt} | WR: %{wr:.1f} | {liq_str}")

print("\n==========================================================================================")
print(" 2. KALDIRAÇ ÖLÇÜM MOTORLARI KARŞILAŞTIRMASI")
print("==========================================================================================")
for lev_name in ['fixed_10x', 'volatility_optimal', 'smart_momentum']:
    bal, cnt, wr, liq = simulate(sl_mode='fixed_2pct', lev_mode=lev_name)
    liq_str = "LİKİT OLDU!" if liq else "Sıfır Likit"
    print(f"Kaldıraç Modu: {lev_name:20} | Bakiye: ${bal:>16,.2f} ({bal*48:,.0f} TL) | İşlem: {cnt} | WR: %{wr:.1f} | {liq_str}")
