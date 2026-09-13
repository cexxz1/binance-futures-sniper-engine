# C:\Users\depco\OneDrive\Desktop\mtf_signal_engine\compare_sqlite_vs_binance.py
import urllib.request, json, sqlite3, datetime, os

DB_PATH = r"C:\Users\depco\OneDrive\Desktop\mtf_signal_engine\mtf_signals.sqlite"

def fetch_live_binance_kline(symbol: str, start_ts: int, end_ts: int):
    # ponytail: naive urllib get, direct from official binance futures rest api
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&startTime={start_ts}&endTime={end_ts}&limit=5"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def inspect_and_compare():
    print(f"=== 1. SQLITE LEDGER CHECK ({DB_PATH}) ===")
    if not os.path.exists(DB_PATH):
        print("ERROR: SQLite database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"Tables in SQLite: {tables}")

    for t in tables:
        c.execute(f"SELECT count(*) FROM {t}")
        cnt = c.fetchone()[0]
        print(f"Table '{t}' has {cnt} rows.")
        if cnt > 0:
            c.execute(f"SELECT * FROM {t} LIMIT 5")
            for row in c.fetchall():
                print(f"  Sample row from {t}: {row}")

    # Check if history or trades exist for MOVR
    print("\n=== 2. QUERYING MOVRUSDT ON 2026-08-27 ===")
    movr_rows = []
    if 'history' in tables:
        c.execute("SELECT * FROM history WHERE sym LIKE '%MOVR%' OR time LIKE '%2026-08-27%'")
        movr_rows = c.fetchall()
        print(f"Found {len(movr_rows)} rows in 'history' matching MOVR/2026-08-27.")
        for r in movr_rows:
            print("  History row:", r)
    elif 'trades' in tables:
        c.execute("SELECT * FROM trades WHERE pair LIKE '%MOVR%' OR open_time LIKE '%2026-08-27%'")
        movr_rows = c.fetchall()
        print(f"Found {len(movr_rows)} rows in 'trades'.")

    conn.close()

    # 3. DIRECT BINANCE REST API QUERY FOR EXACT SAME CANDLE
    # 2026-08-27 03:00:00 UTC -> timestamp ms
    dt_start = datetime.datetime(2026, 8, 27, 3, 0, 0, tzinfo=datetime.timezone.utc)
    dt_end = datetime.datetime(2026, 8, 27, 4, 0, 0, tzinfo=datetime.timezone.utc)
    start_ts = int(dt_start.timestamp() * 1000)
    end_ts = int(dt_end.timestamp() * 1000)

    print(f"\n=== 3. LIVE BINANCE FUTURES REST CALL ===")
    print(f"Calling: fapi.binance.com for MOVRUSDT at {dt_start} ({start_ts})...")
    raw_kline = fetch_live_binance_kline("MOVRUSDT", start_ts, end_ts)
    print("Raw Binance JSON response:")
    for k in raw_kline:
        k_dt = datetime.datetime.fromtimestamp(k[0]/1000, datetime.timezone.utc)
        print(f"  Time: {k_dt} | Open: {k[1]} | High: {k[2]} | Low: {k[3]} | Close: {k[4]} | Vol: {k[5]}")

if __name__ == '__main__':
    inspect_and_compare()
