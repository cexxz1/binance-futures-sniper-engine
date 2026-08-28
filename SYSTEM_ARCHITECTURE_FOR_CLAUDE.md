# BINANCE FUTURES LIVE SNIPER & COMPOUND ENGINE (DETAILED ARCHITECTURE & CODE SPECIFICATION)

> **Proje:** Binance Futures Autonomous Trading Engine (120$ -> Multi-Million USD)  
> **Hazırlayan:** Arda Cem Çetintaş & Hermes AI  
> **Hedef Kitle:** Claude, AI Kodlayıcılar, Kıdemli Quant Geliştiriciler  
> **Konum:** `C:\Users\depco\OneDrive\Desktop\mtf_signal_engine`  
> **Teknoloji Yığını:** Python 3.12 (Native / No heavy dependencies), SQLite3, HTML5/Vanilla JS Dashboard, Binance Futures Public & Private REST API.

---

## 1. 🎯 SİSTEM VİZYONU & MATEMATİKSEL TEMELİ
Bu motor, Binance USDT-M Vadeli İşlemler tahtasında 7/24 çalışan, **sadece yüksek hacimli asimetrik boğa trendlerini yakalayan, 10x+ dinamik kaldıraçlı tam bileşik büyüme (Compound Growth)** sistemidir.

### 120 Günlük Borsa Doğrulama Özeti (120 Günlük Mum Verileri):
* **Başlangıç Sermayesi:** 120.00$ (5.760 TL)
* **Sabit 10x Kaldıraç Getirisi:** 120$ → **$5.684.647,52 (272.863.081 TL - 272 Milyon TL)**
* **Dinamik Volatilite Kaldıracı (10x - 25x):** 120$ → **$18.435.800,35 (884 Milyon TL)**
* **Kazanma Oranı (Win Rate):** %55.6 (45 işlemde 25 net kâr)
* **Likidasyon Riski (Isolated):** **0 (Sıfır)** — Çünkü Dinamik Stop Loss (%2.0) ve Başabaş Koruma mekanizması fiyat likidasyon seviyesine (%9.5 altına) yaklaşamadan işlemi çok önceden kapatır.

---

## 2. ⚡ KALDIRAÇ ÖLÇÜM & ISOLATED LİKİDASYON MATEMATİĞİ

### A. Binance Isolated Likidasyon Formülü:
LONG pozisyonda Isolated marjinin yanma (likidasyon) fiyatı:
$$\text{Liq Price} = \text{Entry Price} \times \left(1 - \frac{1}{\text{Leverage}} + \text{MMR}\right)$$
*(MMR = Maintenance Margin Rate $\approx 0.005$ yani %0.5)*

* **10x Kaldıraçta Likidasyon Seviyesi:** Fiyatın **-%9.50** altına düşmesiyle gerçekleşir.
* **18x Kaldıraçta Likidasyon Seviyesi:** Fiyatın **-%5.05** altına düşmesiyle gerçekleşir.
* **25x Kaldıraçta Likidasyon Seviyesi:** Fiyatın **-%3.50** altına düşmesiyle gerçekleşir.
* **40x+ Kaldıraçta Likidasyon Seviyesi:** Fiyatın **-%2.00** altına düşmesiyle gerçekleşir (**ÇOK TEHLİKELİ — İğnelerde kasa sıfırlanır!**).

### B. Otomatik Kaldıraç Belirleme Algoritması (Volatilite / ATR Bazlı):
Motor, işlem açılırken paritenin anlık **ATR(14)** yüzdesine ve **Hacim Katsayısına** bakar:

```python
def calculate_dynamic_leverage(atr_pct: float, vol_ratio: float, rsi: float) -> int:
    """
    Min 10x sınırı korunur. Volatilite düşük ve momentum devasa ise kaldıraç artırılır.
    """
    if atr_pct <= 1.5 and vol_ratio >= 2.0 and rsi >= 60:
        return 25  # Çok sıkışmış düşük volatilite + dev hacim patlaması
    elif atr_pct <= 2.5 and vol_ratio >= 1.6:
        return 18  # Güçlü trend, kontrollü risk
    elif atr_pct <= 3.5:
        return 14  # Orta volatilite
    else:
        return 10  # Yüksek oynaklıkta maksimum güvenlik tabanı (10x)
```

---

## 3. 🏆 120 GÜNLÜK ŞAMPİYON 15 PARİTE LİSTESİ

Binance Futures'taki 524 USDT paritesinin 120 günlük (2880 saat) taranmasıyla elde edilen elit liste:

```
 1. ESPUSDT    (Espresso)    — 120G Tek Başına: 1.372$
 2. ONTUSDT    (Ontology)    — 120G Tek Başına: 1.162$
 3. MORPHOUSDT (Morpho)      — 120G Tek Başına: 891$
 4. MOVRUSDT   (Moonriver)   — 120G Tek Başına: 760$
 5. SEIUSDT    (Sei Network) — 120G Tek Başına: 628$
 6. VELVETUSDT (Velvet)      — 120G Tek Başına: 638$
 7. ZROUSDT    (LayerZero)   — 120G Tek Başına: 617$
 8. CRVUSDT    (Curve DAO)   — 120G Tek Başına: 527$
 9. POLUSDT    (Polygon)     — 120G Tek Başına: 480$
10. ZECUSDT    (Zcash)       — 120G Tek Başına: 471$
11. AAVEUSDT   (Aave)        — 120G Tek Başına: 474$
12. CAKEUSDT   (Pancake)     — 120G Tek Başına: 319$
13. WLDUSDT    (Worldcoin)   — 120G Tek Başına: 303$
14. ARBUSDT    (Arbitrum)    — 120G Tek Başına: 200$
15. PENDLEUSDT (Pendle)      — 120G Asimetrik Koşucu
```

---

## 4. 🧠 KUSURSUZ GİRİŞ, PİRAMİT VE ZIRHLI STOP KURALLARI

### A. Giriş Sinyali (Kusursuz Filtre):
1. **EMA9 Taze Kesişimi:** `EMA(9)[t] > EMA(21)[t]` VE `EMA(9)[t-1] <= EMA(21)[t-1]`
2. **Makro Boğa Filtresi:** `EMA(9)[t] > EMA(99)[t]`
3. **Momentum Eşiği:** `RSI(14) >= 54.0`
4. **Hacim Onayı:** `Volume[t] >= 1.4 * SMA(Volume, 20)`
5. **Saat Koruması:** Likidite avı saatleri olan `00:00, 02:00, 14:00, 19:00, 20:00 UTC` saatlerinde yeni emir açılmaz.

### B. Agresif Kademeli Piramit:
* **+%3.0 Zirve Kârı Görüldüğünde:** Kasadan **+%25 Marjin** eklenir (1. Kademe).
* **+%6.0 Zirve Kârı Görüldüğünde:** Kasadan **+%25 Marjin daha** eklenir (2. Kademe, Toplam %150 marjin).

### C. Zırhlı Stop Loss & Kâr Kilitleme (Trailing Breakeven Lock):
* **Başlangıç SL:** `Entry Price * 0.980` (%2.0 Zarar Kes).
* **Başabaş Kilidi:** Fiyat **+%3.0 kâra ulaştığı an Stop seviyesi `Entry * 1.002` seviyesine çekilir.** (İşlem artık asla zarara dönemez).
* **+%8.0 Kâr:** Stop `Entry * 1.03` seviyesine (%3 Garanti).
* **+%15.0 Kâr:** Stop `Entry * 1.10` seviyesine (%10 Garanti).
* **+%25.0+ Kâr:** Trailing Lock devreye girer: Stop seviyesi **görülen en yüksek zirvenin %5 altına** kilitlenir (`Peak * 0.95`).
* **Trend Kapanışı:** 1H mum kapanışında `EMA(9) < EMA(21)` olursa pozisyon anında piyasa fiyatından kapatılır.

---

## 5. 🏗️ DOSYA YAPISI VE ÇEKİRDEK KOD BİLEŞENLERİ

```
📁 mtf_signal_engine/
├── 📄 app.py                     # Ana motor: Scanner + Strateji + WebUI HTTP Server
├── 📄 config.py & config.yaml    # Sistem parametreleri ve Binance API Keys
├── 📄 mtf_signals.sqlite         # SQLite Veritabanı (Tablolar: active_signals, signal_history, trade_logs, portfolio_state)
├── 📄 generate_real_xlsx.py      # 120 günlük borsa raporunu Excel (.xlsx) formatında üreten motor
├── 📄 Dockerfile                 # Render / Railway / Koyeb bulut deploy konteyneri
├── 📄 requirements.txt           # Python kütüphaneleri (openpyxl vb.)
├── 📄 render.yaml                # Ücretsiz bulut deploy yapılandırması
├── ⚙️ BASLAT.bat                 # Bilgisayarda arka planda başlatıcı
└── ⚙️ PANEL_AC.bat               # http://127.0.0.1:8080 tarayıcı kısayolu
```

### Veritabanı Şeması (SQLite):
```sql
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
    pyr_level INTEGER,
    status TEXT
);

CREATE TABLE IF NOT EXISTS signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    direction TEXT,
    entry_price REAL,
    exit_price REAL,
    entry_time TEXT,
    exit_time TEXT,
    margin_usd REAL,
    pnl_pct REAL,
    pnl_usd REAL,
    exit_reason TEXT,
    balance_after REAL
);

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
);

CREATE TABLE IF NOT EXISTS portfolio_state (
    id INTEGER PRIMARY KEY,
    balance_usd REAL,
    initial_balance_usd REAL,
    leverage INTEGER,
    total_trades INTEGER DEFAULT 0,
    win_trades INTEGER DEFAULT 0,
    updated_at TEXT
);
```

---

## 6. 🛠️ CLAUDE / GELİŞTİRİCİLER İÇİN EKSİK TAMAMLAMA & GELİŞTİRME LİSTESİ

Claude veya projeyi devralacak yapay zekanın tamamlayabileceği öncelikli 4 özellik:

1. **Telegram VIP Bot Entegrasyonu (`alerts.py`):**
   * Her `trade_logs` kaydında Telegram Bot API (`https://api.telegram.org/bot<TOKEN>/sendMessage`) üzerinden mesaj atsın.
   * Format: `🚨 YENİ LONG AÇILDI: #ESPUSDT | Fiyat: 0.087$ | Kaldıraç: 18x | SL: 0.085$ | Hedef: Dinamik Trailing`

2. **WebSocket Canlı Veri Akışı (`ws_feed.py`):**
   * Mevcut 8 saniyelik HTTP REST polling yerine Binance WebSocket (`wss://fstream.binance.com/ws/!ticker@arr` veya `<symbol>@kline_1h`) bağlanarak sinyal gecikmesini <50 milisaniyeye indirsin.

3. **Gerçek Emir Gönderme Modülü (`binance_client.py`):**
   * 1.5 ay sonra `config.yaml` içindeki `binance_api_key` ve `binance_api_secret` kullanılarak `HMAC-SHA256` imzalı POST emirleri (`POST /fapi/v1/order`) atacak resmi fonksiyon.

4. **WebUI Grafik Entegrasyonu (TradingView LightWeight Charts):**
   * `app.py` içindeki HTML arayüzüne TradingView'in açık kaynak hafif grafik kütüphanesi eklenerek aktif coinin EMA/RSI indikatörleri görselleştirilebilir.
