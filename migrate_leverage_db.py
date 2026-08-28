import sqlite3

conn = sqlite3.connect('mtf_signals.sqlite')
c = conn.cursor()

# Tabloları drop edip yeni şema ile temiz oluştur
c.execute('DROP TABLE IF EXISTS active_signals')
c.execute('DROP TABLE IF EXISTS signal_history')

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

conn.commit()
conn.close()
print("Veritabani semasi leverage kolonu ile basariyla guncellendi.")
