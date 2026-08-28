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

# Check why trades were skipped
# Let's compare 4 scenarios:
# 1. Base (Komisyonsuz, BTC filtresiz, Circuit breaker yok) -> 737k
# 2. Base + Gerçekçi Komisyon & Funding & Slippage -> ?
# 3. Base + Komisyon + Circuit Breaker -> ?
# 4. Base + Komisyon + BTC Filtresi -> ?

def simulate_variant(use_fees=False, use_btc_filter=False, use_circuit_breaker=False):
    balance = 120.0
    pos = None
    trades = []
    daily_start_bal = balance
    last_day = None
    consecutive_losses = 0
    circuit_breaker_until = 0

    TAKER_FEE_PCT = 0.0005 if use_fees else 0.0005 # Base fee was 0.0005*2
    FUNDING_RATE_8H = 0.0001 if use_fees else 0.0
    BASE_SLIPPAGE = 0.0003 if use_fees else 0.0

    for i in range(50, min_len):
        ts = timestamps[i]
        dt = datetime.datetime.fromtimestamp(ts/1000, datetime.timezone.utc)
        current_day = dt.date()

        if current_day != last_day:
            daily_start_bal = balance
            last_day = current_day

        if use_circuit_breaker and ts < circuit_breaker_until:
            continue

        if use_circuit_breaker and balance < daily_start_bal * 0.90:
            circuit_breaker_until = ts + (24 * 3600 * 1000)
            continue

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
                reason = 'SL'
            elif e_fast < e_slow:
                exit_trade = True
                exit_p = cur_price
                reason = 'EMA'

            if exit_trade:
                raw_gain = (exit_p - pos['entry']) / pos['entry']
                funding_intervals = max(1, int(duration_hours / 8.0))
                total_cost_pct = (TAKER_FEE_PCT * 2) + (funding_intervals * FUNDING_RATE_8H) + BASE_SLIPPAGE
                net_gain = raw_gain - total_cost_pct
                pnl = pos['margin'] * lev * net_gain
                balance += pnl

                if pnl < 0:
                    consecutive_losses += 1
                    if consecutive_losses >= 3 and use_circuit_breaker:
                        circuit_breaker_until = ts + (12 * 3600 * 1000)
                        consecutive_losses = 0
                else:
                    consecutive_losses = 0

                trades.append({'sym': s, 'pnl': pnl, 'balance': balance, 'entry_dt': pos['entry_dt'], 'exit_dt': dt})
                pos = None

        if pos is None and balance > 5:
            if dt.hour in [0, 2, 14, 19, 20]: continue
            
            if use_btc_filter:
                btc_e9 = indicators['BTCUSDT']['e9'][i]
                btc_e21 = indicators['BTCUSDT']['e21'][i]
                if btc_e9 < btc_e21 * 0.998:
                    continue

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

    return balance, len(trades), trades

print("--- NEDEN DÜŞTÜĞÜNÜN PARÇA PARÇA ANALİZİ ---")
b1, c1, t1 = simulate_variant(use_fees=False, use_btc_filter=False, use_circuit_breaker=False)
print(f"1. Orijinal Akıllı Kaldıraç Motoru (14 İşlem) : ${b1:>12,.2f} ({b1*48:,.0f} TL)")

b2, c2, t2 = simulate_variant(use_fees=True, use_btc_filter=False, use_circuit_breaker=False)
print(f"2. Gerçekçi Komisyon + Fonlama + Slippage Eklendi : ${b2:>12,.2f} ({b2*48:,.0f} TL)")

b3, c3, t3 = simulate_variant(use_fees=True, use_btc_filter=False, use_circuit_breaker=True)
print(f"3. + Devre Kesici (Circuit Breaker) Eklendi : ${b3:>12,.2f} ({b3*48:,.0f} TL)")

b4, c4, t4 = simulate_variant(use_fees=True, use_btc_filter=True, use_circuit_breaker=False)
print(f"4. + SADECE BTC Filtresi Eklendi (Büyük Kaçışlar!): ${b4:>12,.2f} ({b4*48:,.0f} TL)")
