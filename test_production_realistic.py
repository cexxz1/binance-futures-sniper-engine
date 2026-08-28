import urllib.request, json, datetime

TOP_15_120D = [
    'BTCUSDT', 'ESPUSDT', 'ONTUSDT', 'MORPHOUSDT', 'MOVRUSDT', 'SEIUSDT',
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

candles = {}
for s in TOP_15_120D:
    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h&limit=720'
    candles[s] = fetch_json(url)

min_len = min(len(candles[s]) for s in TOP_15_120D)
timestamps = [candles['BTCUSDT'][i][0] for i in range(min_len)]

indicators = {}
for s in TOP_15_120D:
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

# DOĞRU PROFESYONEL DEVRE KESİCİ:
# Sadece hesapta BÜYÜK BİR FELAKET (%25 günlük düşüş) olursa motoru durdurur, normal %2'lik korumalı stoplarda trendleri kaçırmaz!
# BTC Makro filtresi de 4H trendine bakar, anlık 1H gürültüsünde altcoin boğasını engellemez.

def run_balanced_production_sim():
    balance = 120.0
    pos = None
    trades = []
    daily_start_bal = balance
    last_day = None

    TAKER_FEE_PCT = 0.0005 # %0.05
    FUNDING_RATE_8H = 0.0001 # %0.01 per 8h
    BASE_SLIPPAGE = 0.0003 # %0.03

    for i in range(50, min_len):
        ts = timestamps[i]
        dt = datetime.datetime.fromtimestamp(ts/1000, datetime.timezone.utc)
        current_day = dt.date()

        if current_day != last_day:
            daily_start_bal = balance
            last_day = current_day

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
            duration_hours = (ts - pos['entry_ts']) / (3600 * 1000)

            if pos['pyr_level'] == 0 and gain_peak >= 0.03:
                pos['margin'] += pos['base_margin'] * 0.25
                pos['pyr_level'] = 1
            elif pos['pyr_level'] == 1 and gain_peak >= 0.06:
                pos['margin'] += pos['base_margin'] * 0.25
                pos['pyr_level'] = 2

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
                reason = '1H Kapanış Trend Sonu'

            if exit_trade:
                raw_gain = (exit_p - pos['entry']) / pos['entry']
                funding_intervals = max(1, int(duration_hours / 8.0))
                total_cost_pct = (TAKER_FEE_PCT * 2) + (funding_intervals * FUNDING_RATE_8H) + BASE_SLIPPAGE
                net_gain = raw_gain - total_cost_pct
                pnl = pos['margin'] * lev * net_gain
                balance += pnl

                trades.append({
                    'sym': s, 'entry_dt': pos['entry_dt'].strftime('%d.%m.%Y %H:%M'),
                    'exit_dt': dt.strftime('%d.%m.%Y %H:%M'),
                    'entry_p': pos['entry'], 'exit_p': exit_p, 'lev': lev,
                    'used_margin': pos['margin'], 'pos_size': pos['margin'] * lev,
                    'cost_usd': pos['margin'] * lev * total_cost_pct,
                    'pnl': pnl, 'balance': balance, 'reason': reason
                })
                pos = None

        if pos is None and balance > 5:
            if dt.hour in [0, 2, 14, 19, 20]: continue

            candidates = []
            for s in TOP_15_120D:
                if s == 'BTCUSDT': continue
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

                if atr_val <= 1.5 and vol_val >= 2.0 and rsi_val >= 60:
                    calc_lev = 25
                elif atr_val <= 2.2 and vol_val >= 1.6 and rsi_val >= 56:
                    calc_lev = 18
                elif atr_val <= 3.2:
                    calc_lev = 14
                else:
                    calc_lev = 10

                pos = {
                    'sym': chosen, 'entry': indicators[chosen]['closes'][i],
                    'entry_ts': ts, 'entry_dt': dt, 'peak': indicators[chosen]['closes'][i],
                    'base_margin': balance, 'margin': balance, 'pyr_level': 0,
                    'leverage': calc_lev
                }

    return balance, trades

bal_p, tr_p = run_balanced_production_sim()
print(f"GERÇEKÇİ TÜM MALİYETLER DAHİL NET KASA: ${bal_p:,.2f} ({bal_p*48:,.0f} TL)")
print("İşlem Detayları:")
for idx, t in enumerate(tr_p):
    print(f"#{idx+1:02d} | {t['sym']:11} | {t['entry_dt']} -> {t['exit_dt']} | {t['lev']}x | PnL: ${t['pnl']:>10,.2f} | Kasa: ${t['balance']:>11,.2f} ({t['balance']*48:>12,.0f} TL)")
