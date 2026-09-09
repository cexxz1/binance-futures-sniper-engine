import os, json, sqlite3, datetime, urllib.request, threading, time
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get('PORT', 10000))
DB_PATH = 'mtf_signals.sqlite'
CHAMPIONS = [
    'ONTUSDT', 'AAVEUSDT', 'MOVRUSDT', 'VELVETUSDT', 'POLUSDT',
    'ARBUSDT', 'MORPHOUSDT', 'CAKEUSDT', 'CRVUSDT', 'INJUSDT',
    'ZECUSDT', 'SEIUSDT', 'ZROUSDT'
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('''CREATE TABLE IF NOT EXISTS state (id INT PRIMARY KEY, bal REAL, peak REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS active (sym TEXT PRIMARY KEY, dir TEXT, entry REAL, peak REAL, sl REAL, margin REAL, lev INT, pyr INT, time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, sym TEXT, dir TEXT, entry REAL, exit REAL, pnl REAL, bal REAL, time TEXT)''')
    c.execute('''INSERT OR IGNORE INTO state VALUES (1, 100.0, 100.0)''')
    conn.commit()
    conn.close()

init_db()

def get_klines(sym: str):
    # ponytail: naive urllib get, 5s timeout prevents hung worker thread
    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1h&limit=120'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())

def scan_and_update():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    c = conn.cursor()
    c.execute('SELECT bal FROM state WHERE id=1')
    row = c.fetchone()
    bal = row[0] if row else 100.0

    c.execute('SELECT sym, dir, entry, peak, sl, margin, lev, pyr FROM active')
    pos = c.fetchone()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    hour, day = now_utc.hour, now_utc.strftime('%A')

    if pos:
        sym, direction, entry, peak, sl, margin, lev, pyr = pos
        try:
            raw = get_klines(sym)
            p, h, l = float(raw[-1][4]), float(raw[-1][2]), float(raw[-1][3])

            if direction == 'LONG':
                new_peak = max(peak, h)
                gain = (new_peak - entry) / entry
                init_m = margin / (1.0 + pyr * 0.35)
                if pyr == 0 and gain >= 0.03:
                    margin += init_m * 0.35
                    pyr = 1
                elif pyr == 1 and gain >= 0.06:
                    margin += init_m * 0.35
                    pyr = 2
                elif pyr == 2 and gain >= 0.12:
                    margin += init_m * 0.50
                    pyr = 3

                if gain >= 0.05:
                    sl = max(sl, new_peak * 0.90)

                exit_now, exit_p = False, p
                if l <= sl: exit_now, exit_p = True, sl

            elif direction == 'SHORT':
                new_peak = min(peak, l)
                gain = (entry - new_peak) / entry
                init_m = margin / (1.0 + pyr * 0.35)
                if pyr == 0 and gain >= 0.03:
                    margin += init_m * 0.35
                    pyr = 1
                elif pyr == 1 and gain >= 0.06:
                    margin += init_m * 0.35
                    pyr = 2

                if gain >= 0.05:
                    sl = min(sl, new_peak * 1.10)

                exit_now, exit_p = False, p
                if h >= sl: exit_now, exit_p = True, sl

            if exit_now:
                rg = (exit_p - entry)/entry if direction == 'LONG' else (entry - exit_p)/entry
                pnl = margin * lev * (rg - 0.0013)
                bal += pnl
                c.execute('DELETE FROM active')
                c.execute('INSERT INTO history (sym, dir, entry, exit, pnl, bal, time) VALUES (?, ?, ?, ?, ?, ?, ?)',
                          (sym, direction, entry, exit_p, pnl, bal, now_utc.isoformat()))
                c.execute('UPDATE state SET bal=? WHERE id=1', (bal,))
            else:
                c.execute('UPDATE active SET peak=?, sl=?, margin=?, pyr=? WHERE sym=?', (new_peak, sl, margin, pyr, sym))
        except Exception:
            pass

    elif bal > 1.0 and hour not in {0, 2, 14, 19, 20} and not (day == 'Friday' and hour >= 18) and day != 'Saturday':
        for s in CHAMPIONS:
            try:
                raw = get_klines(s)
                closes = [float(x[4]) for x in raw]
                highs, lows, vols = [float(x[2]) for x in raw], [float(x[3]) for x in raw], [float(x[5]) for x in raw]

                k9, k21, k99 = 2/10, 2/22, 2/100
                e9, e21, e99 = closes[0], closes[0], closes[0]
                pe9, pe21 = e9, e21
                for cl in closes[1:]:
                    pe9, pe21 = e9, e21
                    e9 = cl * k9 + e9 * (1 - k9)
                    e21 = cl * k21 + e21 * (1 - k21)
                    e99 = cl * k99 + e99 * (1 - k99)

                v_sma = sum(vols[-21:-1]) / 20.0
                v_r = vols[-1] / v_sma if v_sma > 0 else 1.0
                p, o, h_bar, l_bar = closes[-1], closes[-2], highs[-1], lows[-1]

                body = abs(p - o)
                long_bad = (h_bar - max(p, o)) > (body * 1.8) if body > 0 else False
                short_bad = (min(p, o) - l_bar) > (body * 1.8) if body > 0 else False

                long_ok = (pe9 <= pe21) and (e9 > e21) and (e9 > e99) and v_r >= 1.5 and not long_bad
                short_ok = (pe9 >= pe21) and (e9 < e21) and (e9 < e99) and v_r >= 1.5 and not short_bad

                if long_ok:
                    margin = bal * 0.90
                    sl = p * 0.980
                    c.execute('INSERT INTO active VALUES (?, "LONG", ?, ?, ?, ?, 14, 0, ?)',
                              (s, p, p, sl, margin, now_utc.isoformat()))
                    break
                elif short_ok and day not in ['Sunday', 'Thursday']:
                    margin = bal * 0.30
                    sl = p * 1.020
                    c.execute('INSERT INTO active VALUES (?, "SHORT", ?, ?, ?, ?, 14, 0, ?)',
                              (s, p, p, sl, margin, now_utc.isoformat()))
                    break
            except Exception:
                pass

    conn.commit()
    conn.close()

def loop_worker():
    while True:
        try:
            scan_and_update()
        except Exception:
            pass
        time.sleep(30)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT bal FROM state WHERE id=1')
        bal = c.fetchone()[0]
        c.execute('SELECT sym, dir, entry, peak, sl, margin, lev, pyr, time FROM active')
        act = c.fetchone()
        c.execute('SELECT sym, dir, entry, exit, pnl, bal, time FROM history ORDER BY id DESC LIMIT 50')
        hist = c.fetchall()
        conn.close()

        res = {
            'status': 'ONLINE_24_7',
            'engine': 'Apex All-In 14x',
            'balance_usd': round(bal, 2),
            'active_position': {
                'symbol': act[0], 'dir': act[1], 'entry': act[2], 'peak': act[3],
                'sl': act[4], 'margin': act[5], 'leverage': act[6], 'pyramid_step': act[7],
                'opened_at': act[8]
            } if act else None,
            'recent_history': [
                {'symbol': h[0], 'dir': h[1], 'entry': h[2], 'exit': h[3], 'pnl': h[4], 'balance': h[5], 'closed_at': h[6]}
                for h in hist
            ]
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(res, indent=2).encode())

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    assert len(CHAMPIONS) == 13
    t = threading.Thread(target=loop_worker, daemon=True)
    t.start()
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"Apex Monitor ready on port {PORT}")
    server.serve_forever()
