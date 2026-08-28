import urllib.request, json, time, datetime

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
    # Pad to match length
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
    e9 = calc_ema(closes, 9)
    e21 = calc_ema(closes, 21)
    e99 = calc_ema(closes, 99)
    r14 = calc_rsi(closes, 14)
    atr14 = calc_atr(highs, lows, closes, 14)
    indicators[s] = {
        'closes': closes, 'highs': highs, 'lows': lows, 'vols': vols,
        'e9': e9, 'e21': e21, 'e99': e99, 'r14': r14, 'atr': atr14
    }

# 3 Farklı Kaldıraç Modeli Simülasyonu:
# Model 1: Sabit 10x
# Model 2: Dinamik Volatilite Kaldıracı (ATR & Vol bazlı, Min 10x, Max 25x)
# Model 3: Agresif Dinamik Kaldıraç (Sinyal gücü + ATR bazlı, Min 10x, Max 50x)

def run_simulation(model_type='fixed_10x'):
    balance = 120.0
    pos = None
    trades = []
    peak_balance = 120.0
    max_drawdown = 0.0
    liquidations = 0

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
            
            # ISOLATED LİKİDASYON KONTROLÜ (Binance MMR ~%0.5 - %1.0)
            # Long için Liq Fiyatı = Entry * (1 - 1/Lev + MMR)
            mmr = 0.005 if lev <= 20 else (0.01 if lev <= 50 else 0.02)
            liq_price = pos['entry'] * (1 - (1 / lev) + mmr)
            
            # Eğer mumun en düşüğü Liq fiyatına değerse ISOLATED LIKIDASYON
            if cur_low <= liq_price:
                balance = 0.0
                liquidations += 1
                trades.append({'sym': s, 'pnl': -pos['margin'], 'reason': f'ISOLATED LIQUIDATION ({lev}x, Liq: {liq_price:.4f})'})
                pos = None
                break # Kasa sıfırlandı
            
            pos['peak'] = max(pos['peak'], cur_high)
            gain_peak = (pos['peak'] - pos['entry']) / pos['entry']
            
            # Piramit
            if pos['pyr_level'] == 0 and gain_peak >= 0.03:
                pos['margin'] += pos['base_margin'] * 0.25
                pos['pyr_level'] = 1
            elif pos['pyr_level'] == 1 and gain_peak >= 0.06:
                pos['margin'] += pos['base_margin'] * 0.25
                pos['pyr_level'] = 2
                
            # Dinamik Stop (Liq seviyesinden ÇOK ÖNCE keser)
            sl = pos['entry'] * 0.980 # %2.0 Başlangıç SL
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
                reason = 'Trailing SL'
            elif e9 < e21:
                exit_trade = True
                exit_p = cur_price
                reason = 'EMA9 < EMA21'
                
            if exit_trade:
                rg = (exit_p - pos['entry']) / pos['entry']
                fee = 0.0005 * 2 # Binance Taker fee %0.05 x 2
                pnl = pos['margin'] * lev * (rg - fee)
                balance += pnl
                if balance > peak_balance: peak_balance = balance
                dd = (peak_balance - balance) / peak_balance * 100
                if dd > max_drawdown: max_drawdown = dd
                
                trades.append({
                    'sym': s, 'entry_dt': pos['entry_dt'], 'exit_dt': dt,
                    'pnl': pnl, 'balance': balance, 'reason': reason,
                    'lev': lev, 'gain_pct': rg * 100, 'liq_price': liq_price
                })
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
                chosen = candidates[0][0]
                rsi_val = candidates[0][1]
                vol_val = candidates[0][2]
                atr_val = candidates[0][3]
                
                # KALDIRAÇ HESAPLAMA MOTORU (Dinamik Risk Analizi):
                # Kural: Min 10x
                # Güçlü Trend & Düşük Volatilite (Düşük ATR) = Yüksek Kaldıraç
                # Yüksek Volatilite = Güvenli Kaldıraç (10x-15x)
                if model_type == 'fixed_10x':
                    calc_lev = 10
                elif model_type == 'dynamic_safe': # 10x - 25x
                    # Volatilite güvenliyse (%2'den küçükse) ve RSI > 60 ise kaldıracı artır
                    base = 10
                    if atr_val <= 1.5 and vol_val >= 2.0 and rsi_val >= 60:
                        calc_lev = 25
                    elif atr_val <= 2.5 and vol_val >= 1.6:
                        calc_lev = 18
                    elif atr_val <= 3.5:
                        calc_lev = 14
                    else:
                        calc_lev = 10
                elif model_type == 'dynamic_uncapped': # 10x - 40x (Sınırları zorlayan)
                    # Çok agresif: Düşük ATR'de kaldıracı 35x-40x'e kadar açar
                    if atr_val <= 1.2 and vol_val >= 2.2:
                        calc_lev = 40
                    elif atr_val <= 1.8 and vol_val >= 1.8:
                        calc_lev = 25
                    elif atr_val <= 2.8:
                        calc_lev = 16
                    else:
                        calc_lev = 10
                        
                pos = {
                    'sym': chosen, 'entry': indicators[chosen]['closes'][i],
                    'entry_ts': ts, 'entry_dt': dt, 'peak': indicators[chosen]['closes'][i],
                    'base_margin': balance, 'margin': balance, 'pyr_level': 0,
                    'leverage': calc_lev
                }

    return {
        'model': model_type,
        'final_bal': balance,
        'trades': len(trades),
        'wins': sum(1 for t in trades if t['pnl'] > 0),
        'max_dd': max_drawdown,
        'liquidations': liquidations,
        'trades_list': trades
    }

m1 = run_simulation('fixed_10x')
m2 = run_simulation('dynamic_safe')
m3 = run_simulation('dynamic_uncapped')

print("==========================================================================")
print(" 120 GÜNLÜK KALDIRAÇ ÖLÇÜM & ISOLATED LİKİDASYON SİMÜLASYONU")
print("==========================================================================")
for m in [m1, m2, m3]:
    wr = (m['wins'] / m['trades'] * 100) if m['trades'] > 0 else 0
    print(f"MODEL: {m['model'].upper():20} | Bakiye: ${m['final_bal']:>15,.2f} ({m['final_bal']*48:,.0f} TL) | WR: %{wr:.1f} ({m['wins']}/{m['trades']}) | MaxDD: %{m['max_dd']:.1f} | Likidasyon: {m['liquidations']}")
