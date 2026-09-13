# C:\Users\depco\OneDrive\Desktop\mtf_signal_engine\verify_sl_breakeven_fix.py
from run_1m_clean_audit import CHAMPIONS, fetch_klines
import datetime, math

def run_fixed_1m():
    hours = 30 * 24
    market = {}
    for s in CHAMPIONS:
        raw = fetch_klines(s, limit=hours)
        closes = [float(x[4]) for x in raw]
        highs = [float(x[2]) for x in raw]
        lows = [float(x[3]) for x in raw]
        vols = [float(x[5]) for x in raw]
        times = [x[0] for x in raw]

        k9, k21, k99 = 2/10, 2/22, 2/100
        e9, e21, e99 = closes[0], closes[0], closes[0]
        e9_arr, e21_arr, e99_arr = [e9], [e21], [e99]
        for c in closes[1:]:
            e9 = c * k9 + e9 * (1 - k9)
            e21 = c * k21 + e21 * (1 - k21)
            e99 = c * k99 + e99 * (1 - k99)
            e9_arr.append(e9); e21_arr.append(e21); e99_arr.append(e99)
        market[s] = {'times': times, 'closes': closes, 'highs': highs, 'lows': lows, 'vols': vols, 'e9': e9_arr, 'e21': e21_arr, 'e99': e99_arr}

    all_times = sorted(list({t for s in CHAMPIONS for t in market[s]['times']}))
    bal = 100.0
    active_pos = None
    trades = []
    consec_loss = 0
    pause_until = 0

    for t in all_times:
        dt = datetime.datetime.fromtimestamp(t/1000, datetime.timezone.utc)
        m, hour, day = dt.month, dt.hour, dt.strftime('%A')
        lev = 12 if m in [3, 4, 9] else 20
        if t < pause_until: continue

        if active_pos:
            s = active_pos['sym']
            d = market[s]
            if t in d['times']:
                idx = d['times'].index(t)
                if t > active_pos['entry_ts']:
                    p, h, l, vol = d['closes'][idx], d['highs'][idx], d['lows'][idx], d['vols'][idx]
                    entry = active_pos['entry']
                    dirn = active_pos['dir']
                    init_m = active_pos['init_m']

                    if dirn == 'LONG':
                        peak = max(active_pos['peak'], h); gain = (peak - entry) / entry
                        # FIX: When Tranche 1 triggers at +3%, SL moves to entry * 1.015 (locks profit for tranche 1, guarantees overall positive)
                        if active_pos['pyr'] == 0 and gain >= 0.03:
                            add_m = init_m * 0.70
                            if bal >= add_m:
                                active_pos['tranches'].append({'margin': add_m, 'entry': entry * 1.03})
                                active_pos['margin'] += add_m; active_pos['pyr'] = 1
                                active_pos['sl'] = max(active_pos['sl'], entry * 1.015)
                        elif active_pos['pyr'] == 1 and gain >= 0.06:
                            add_m = init_m * 0.70
                            if bal >= add_m:
                                active_pos['tranches'].append({'margin': add_m, 'entry': entry * 1.06})
                                active_pos['margin'] += add_m; active_pos['pyr'] = 2
                                active_pos['sl'] = max(active_pos['sl'], entry * 1.030)

                        if gain >= 0.05: active_pos['sl'] = max(active_pos['sl'], peak * 0.92)
                        exit_now = (l <= active_pos['sl'])
                        exit_p = active_pos['sl'] if exit_now else p
                    else:
                        trough = min(active_pos['peak'], l); gain = (entry - trough) / entry
                        if active_pos['pyr'] == 0 and gain >= 0.03:
                            add_m = init_m * 0.70
                            if bal >= add_m:
                                active_pos['tranches'].append({'margin': add_m, 'entry': entry * 0.97})
                                active_pos['margin'] += add_m; active_pos['pyr'] = 1
                                active_pos['sl'] = min(active_pos['sl'], entry * 0.985)
                        elif active_pos['pyr'] == 1 and gain >= 0.06:
                            add_m = init_m * 0.70
                            if bal >= add_m:
                                active_pos['tranches'].append({'margin': add_m, 'entry': entry * 0.94})
                                active_pos['margin'] += add_m; active_pos['pyr'] = 2
                                active_pos['sl'] = min(active_pos['sl'], entry * 0.970)

                        if gain >= 0.05: active_pos['sl'] = min(active_pos['sl'], trough * 1.08)
                        exit_now = (h >= active_pos['sl'])
                        exit_p = active_pos['sl'] if exit_now else p

                    if exit_now:
                        duration_h = (t - active_pos['entry_ts']) / (3600 * 1000)
                        funding = max(1, int(duration_h / 8.0)) * 0.0001
                        bar_vol_usd = vol * p
                        size_ratio = (active_pos['margin'] * lev) / max(bar_vol_usd, 1.0)
                        exit_slip = 0.0006 + (0.005 * math.sqrt(size_ratio) if size_ratio > 0.01 else 0.0)
                        fee_rate = 0.0010 + exit_slip + funding

                        total_pnl = 0.0
                        for tranche in active_pos['tranches']:
                            t_m = tranche['margin']
                            t_e = tranche['entry']
                            t_rg = (exit_p - t_e) / t_e if dirn == 'LONG' else (t_e - exit_p) / t_e
                            t_pnl = t_m * lev * (t_rg - fee_rate)
                            total_pnl += t_pnl

                        bal += total_pnl
                        trades.append({
                            'sym': s, 'dir': dirn, 'in': entry, 'out': exit_p,
                            'pnl': total_pnl, 'bal': bal, 'time': dt.strftime('%m-%d %H:%M')
                        })
                        active_pos = None
                        if total_pnl > 0: consec_loss = 0
                        else:
                            consec_loss += 1
                            if consec_loss >= 3:
                                pause_until = t + 24 * 3600 * 1000
                                consec_loss = 0

        num_slots = 1 if bal < 3000 else 2
        slot_cap = bal / num_slots

        if not active_pos and bal > 10.0 and t >= pause_until:
            if hour in {0, 2, 14, 19, 20} or (day == 'Friday' and hour >= 18) or day == 'Saturday':
                continue

            for s in CHAMPIONS:
                d = market[s]
                if t not in d['times']: continue
                idx = d['times'].index(t)
                if idx < 22: continue

                p, o, h_bar, l_bar, vol = d['closes'][idx], d['closes'][idx-1], d['highs'][idx], d['lows'][idx], d['vols'][idx]
                e9, e21, e99 = d['e9'][idx], d['e21'][idx], d['e99'][idx]
                pe9, pe21 = d['e9'][idx-1], d['e21'][idx-1]
                v_sma = sum(d['vols'][idx-20:idx]) / 20.0 if idx >= 20 else 1.0
                v_r = vol / v_sma if v_sma > 0 else 1.0

                body = abs(p - o)
                long_bad = (h_bar - max(p, o)) > (body * 1.8) if body > 0 else False
                short_bad = (min(p, o) - l_bar) > (body * 1.8) if body > 0 else False

                long_ok = (pe9 <= pe21) and (e9 > e21) and (e9 > e99) and v_r >= 2.0 and not long_bad
                short_ok = (pe9 >= pe21) and (e9 < e21) and (e9 < e99) and v_r >= 2.0 and not short_bad

                bar_vol_usd = vol * p
                max_safe_m = min(100000.0, max(500.0, (bar_vol_usd * 0.02) / lev))
                scale = 0.50 if m == 9 else 1.0

                if long_ok:
                    m_val = min(slot_cap * 0.90 * scale, max_safe_m)
                    real_entry_p = p * 1.0006
                    active_pos = {
                        'sym': s, 'dir': 'LONG', 'entry': real_entry_p, 'peak': real_entry_p,
                        'sl': real_entry_p * 0.98, 'init_m': m_val, 'margin': m_val, 'pyr': 0, 'entry_ts': t,
                        'tranches': [{'margin': m_val, 'entry': real_entry_p}]
                    }
                    break
                elif short_ok and day not in ['Sunday', 'Thursday']:
                    m_val = min(slot_cap * 0.30 * scale, max_safe_m)
                    real_entry_p = p * 0.9994
                    active_pos = {
                        'sym': s, 'dir': 'SHORT', 'entry': real_entry_p, 'peak': real_entry_p,
                        'sl': real_entry_p * 1.02, 'init_m': m_val, 'margin': m_val, 'pyr': 0, 'entry_ts': t,
                        'tranches': [{'margin': m_val, 'entry': real_entry_p}]
                    }
                    break

    return trades, bal

if __name__ == '__main__':
    tr, b = run_fixed_1m()
    print(f"FIXED 1-MONTH RESULT: Balance=${b:,.2f} | Trades={len(tr)}")
    for idx, t in enumerate(tr, 1):
        status = "WIN" if t['pnl'] > 0 else "LOSS"
        print(f"[{idx:02d}] {t['time']} | {t['sym']:<10} {t['dir']:<5} | In: ${t['in']:<8.4f} Out: ${t['out']:<8.4f} | PnL: ${t['pnl']:>8.2f} | Bal: ${t['bal']:>8.2f} [{status}]")
