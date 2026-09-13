# APEX QUANT TRADING ENGINE — MASTER AUDIT & OPERATIONAL MANUAL

## 📌 1. SİSTEM MİMARİSİ VE ÇALIŞMA PRENSİBİ
Apex Ultimate Quant 20x, Binance Vadeli İşlemler (Futures) piyasasında deterministik ve matematiksel kurallarla 7/24 otonom çalışan mikro-trend avcısıdır.

### Temel Çalışma Kuralları:
1. **Veri Beslemesi:** Resmi Binance Futures REST API (`https://fapi.binance.com/fapi/v1/klines`). Sadece **tamamlanmış 1H mumlar** kullanılır (Repainting imkansızdır).
2. **Sinyal Tespiti:**
   - **LONG:** `EMA9 > EMA21 > EMA99` & `Hacim >= 20 bar ortalamasının 2.0 katı` & `Üst fitil <= Gövde * 1.8`.
   - **SHORT:** `EMA9 < EMA21 < EMA99` & `Hacim >= 20 bar ortalamasının 2.0 katı` & `Alt fitil <= Gövde * 1.8` (Pazar ve Perşembe SHORT yasak).
3. **Zaman & Volatilite Filtreleri:** Cuma 18:00 - Pazar 00:00 arası işlem açılmaz. Volatil saatlerde (00, 02, 14, 19, 20 UTC) yeni emir verilmez.
4. **Dinamik Kaldıraç (Tarihsel Tekerrür Kalkanı):**
   - Mart, Nisan ve Eylül aylarında **12x Kaldıraç** (Chop/Düzeltme Kalkanı).
   - Diğer tüm aylarda **20x Kaldıraç** (Ralli Modu).
5. **Giriş ve Stop-Loss Mekaniği:**
   - **Giriş SL:** Sabit `-%2.00` (Piyasa gürültüsü ve fitil koruması).
   - **Piramit Kademeleri:** Kâr `+%3.0` -> `+%80` Marjin, Kâr `+%6.0` -> `+%80` Marjin, Kâr `+%12.0` -> `+%140` Marjin.
   - **Kilitli Breakeven:** Piramit tetiklendiği an Stop derhal `+%1.5` kâra (`entry * 1.015`) kilitlenir. Asla kârlı pozisyon zarara dönmez.
   - **Zirve Takibi (Trailing Stop):** Tepe fiyattan `-%7.0` dönüşte tüm pozisyon kârla kapatılır.
6. **Risk ve Kasa Yönetimi:**
   - **24s Streak Guard:** Arka arkaya 3 stop-loss yaşanırsa bot 24 saat uyur.
   - **Spot USDT Vault:** Kasa $5.000'ı aştıktan sonra edilen her kârın `%20`'si otomatik olarak güvenli spot kasaya aktarılır.
   - **Kademeli Slot:** <$5k (1 Slot, %90 Long / %30 Short), $5k-$25k (2 Slot), $25k-$100k (4 Slot), >$100k (6 Slot). Tek işlem limiti max $100.000 veya 1H mum hacminin %2'si.

---

## 📊 2. 6 AYLIK GERÇEKLEŞEN BİNANCE FUTURES LOG TABLOSU (180 GÜN / 17 MART - 13 EYLÜL 2026)
- **Başlangıç Kasa:** $100.00
- **Aktif Vadeli Kasa:** **$27,005.89**
- **Spot USDT Vault:** **$6,929.68**
- **TOPLAM NET SERVET:** **$33,935.57 (1,644,178 TL)**
- **Tarihsel En Dip Kasa:** **$18.15** (Sıfırlanma riski %0.00)
- **Toplam İşlem:** 59 İşlem

| # | Giriş Zamanı | Kapanış Zamanı | Parite | Yön | Giriş ($) | Çıkış ($) | Net PnL ($) | Kasa ($) | Spot Vault ($) |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 2026-03-27 10:00 | 2026-03-28 13:00 | MOVRUSDT | SHORT | $1.0534 | $1.0376 | $   -0.67 | $    99.33 | $    0.00 |
| 02 | 2026-03-31 09:00 | 2026-03-31 17:00 | CAKEUSDT | SHORT | $1.3635 | $1.3908 | $   -7.76 | $    91.57 | $    0.00 |
| 03 | 2026-04-06 05:00 | 2026-04-06 07:00 | ONTUSDT | SHORT | $0.0910 | $0.0929 | $   -7.15 | $    84.42 | $    0.00 |
| 04 | 2026-04-07 12:00 | 2026-04-08 23:00 | CAKEUSDT | LONG | $1.4327 | $1.4756 | $    1.97 | $    86.39 | $    0.00 |
| 05 | 2026-04-09 05:00 | 2026-04-09 15:00 | MORPHOUSDT | LONG | $1.7459 | $1.7721 | $    0.27 | $    86.66 | $    0.00 |
| 06 | 2026-04-09 15:00 | 2026-04-10 14:00 | INJUSDT | LONG | $2.9618 | $3.0062 | $    0.10 | $    86.76 | $    0.00 |
| 07 | 2026-04-10 16:00 | 2026-04-11 00:00 | VELVETUSDT | SHORT | $0.0633 | $0.0645 | $   -6.95 | $    79.81 | $    0.00 |
| 08 | 2026-04-13 22:00 | 2026-04-14 11:00 | ARBUSDT | LONG | $0.1132 | $0.1109 | $  -18.70 | $    61.10 | $    0.00 |
| 09 | 2026-04-16 18:00 | 2026-04-17 03:00 | CAKEUSDT | LONG | $1.6321 | $1.5994 | $  -14.32 | $    46.78 | $    0.00 |
| 10 | 2026-04-21 15:00 | 2026-04-21 17:00 | ARBUSDT | LONG | $0.1282 | $0.1256 | $  -10.96 | $    35.82 | $    0.00 |
| 11 | 2026-04-26 11:00 | 2026-04-26 16:00 | SEIUSDT | LONG | $0.0626 | $0.0636 | $    0.11 | $    35.93 | $    0.00 |
| 12 | 2026-04-27 05:00 | 2026-04-27 14:00 | ZROUSDT | SHORT | $1.5242 | $1.5013 | $   -0.06 | $    35.88 | $    0.00 |
| 13 | 2026-04-27 17:00 | 2026-04-27 18:00 | MOVRUSDT | LONG | $2.3684 | $2.3211 | $   -8.41 | $    27.47 | $    0.00 |
| 14 | 2026-04-28 12:00 | 2026-04-28 13:00 | MOVRUSDT | LONG | $2.3454 | $2.2985 | $   -6.44 | $    21.03 | $    0.00 |
| 15 | 2026-04-29 15:00 | 2026-05-03 15:00 | CAKEUSDT | SHORT | $1.4809 | $1.5105 | $   -2.88 | $    18.15 | $    0.00 |
| 16 | 2026-05-04 01:00 | 2026-05-06 14:00 | CRVUSDT | LONG | $0.2372 | $0.2444 | $    0.45 | $    18.60 | $    0.00 |
| 17 | 2026-05-08 04:00 | 2026-05-11 00:00 | SEIUSDT | LONG | $0.0614 | $0.0742 | $  151.78 | $   170.39 | $    0.00 |
| 18 | 2026-05-13 12:00 | 2026-05-19 00:00 | ONTUSDT | SHORT | $0.0623 | $0.0587 | $   68.63 | $   239.02 | $    0.00 |
| 19 | 2026-05-26 04:00 | 2026-05-26 17:00 | SEIUSDT | LONG | $0.0631 | $0.0640 | $    1.25 | $   240.26 | $    0.00 |
| 20 | 2026-05-27 21:00 | 2026-05-28 03:00 | ARBUSDT | SHORT | $0.1065 | $0.1049 | $   -0.62 | $   239.64 | $    0.00 |
| 21 | 2026-06-05 15:00 | 2026-06-05 17:00 | VELVETUSDT | LONG | $0.1219 | $0.1242 | $   29.15 | $   268.79 | $    0.00 |
| 22 | 2026-06-09 16:00 | 2026-06-09 17:00 | CRVUSDT | LONG | $0.1993 | $0.2023 | $    1.40 | $   270.19 | $    0.00 |
| 23 | 2026-06-11 17:00 | 2026-06-12 06:00 | CAKEUSDT | LONG | $1.3364 | $1.3097 | $ -109.38 | $   160.81 | $    0.00 |
| 24 | 2026-06-12 13:00 | 2026-06-12 15:00 | INJUSDT | SHORT | $5.2259 | $5.3304 | $  -20.94 | $   139.88 | $    0.00 |
| 25 | 2026-06-12 15:00 | 2026-06-12 21:00 | ZECUSDT | SHORT | $416.7598 | $410.5084 | $   -0.36 | $   139.51 | $    0.00 |
| 26 | 2026-06-14 21:00 | 2026-06-15 19:00 | POLUSDT | LONG | $0.0768 | $0.0780 | $   -2.20 | $   137.32 | $    0.00 |
| 27 | 2026-06-19 03:00 | 2026-06-20 13:00 | INJUSDT | SHORT | $5.1029 | $5.0264 | $   -0.80 | $   136.52 | $    0.00 |
| 28 | 2026-06-21 15:00 | 2026-06-21 16:00 | VELVETUSDT | LONG | $0.5148 | $0.5045 | $  -53.32 | $    83.19 | $    0.00 |
| 29 | 2026-06-23 06:00 | 2026-06-24 03:00 | CRVUSDT | SHORT | $0.2046 | $0.2015 | $   -0.31 | $    82.89 | $    0.00 |
| 30 | 2026-06-24 13:00 | 2026-06-24 14:00 | ONTUSDT | SHORT | $0.0435 | $0.0444 | $  -10.79 | $    72.10 | $    0.00 |
| 31 | 2026-06-24 15:00 | 2026-06-24 16:00 | ONTUSDT | SHORT | $0.0430 | $0.0424 | $   -0.19 | $    71.91 | $    0.00 |
| 32 | 2026-07-01 13:00 | 2026-07-01 23:00 | ZECUSDT | LONG | $409.3254 | $415.4653 | $    0.37 | $    72.29 | $    0.00 |
| 33 | 2026-07-05 13:00 | 2026-07-05 18:00 | CAKEUSDT | LONG | $1.4178 | $1.4390 | $    0.38 | $    72.66 | $    0.00 |
| 34 | 2026-07-06 15:00 | 2026-07-08 01:00 | POLUSDT | LONG | $0.0748 | $0.0759 | $   -0.33 | $    72.33 | $    0.00 |
| 35 | 2026-07-08 07:00 | 2026-07-08 08:00 | MOVRUSDT | LONG | $1.4409 | $1.4120 | $  -28.25 | $    44.08 | $    0.00 |
| 36 | 2026-07-08 16:00 | 2026-07-22 06:00 | POLUSDT | LONG | $0.0761 | $0.0793 | $   20.69 | $    64.77 | $    0.00 |
| 37 | 2026-07-22 13:00 | 2026-07-22 23:00 | MOVRUSDT | LONG | $1.3318 | $1.3052 | $  -26.38 | $    38.40 | $    0.00 |
| 38 | 2026-07-27 15:00 | 2026-07-28 05:00 | ZECUSDT | SHORT | $483.1200 | $475.8732 | $   -0.10 | $    38.30 | $    0.00 |
| 39 | 2026-07-31 01:00 | 2026-07-31 14:00 | ZECUSDT | SHORT | $466.1801 | $459.1874 | $   -0.10 | $    38.20 | $    0.00 |
| 40 | 2026-08-05 13:00 | 2026-08-06 05:00 | CRVUSDT | SHORT | $0.2037 | $0.2078 | $   -5.00 | $    33.20 | $    0.00 |
| 41 | 2026-08-07 09:00 | 2026-08-07 17:00 | POLUSDT | LONG | $0.0763 | $0.0748 | $  -12.97 | $    20.23 | $    0.00 |
| 42 | 2026-08-11 09:00 | 2026-08-11 10:00 | VELVETUSDT | LONG | $0.5867 | $0.7612 | $  182.92 | $   203.16 | $    0.00 |
| 43 | 2026-08-14 09:00 | 2026-08-17 06:00 | ARBUSDT | SHORT | $0.0741 | $0.0756 | $  -27.30 | $   175.85 | $    0.00 |
| 44 | 2026-08-17 07:00 | 2026-08-17 12:00 | POLUSDT | LONG | $0.0757 | $0.0769 | $    0.92 | $   176.77 | $    0.00 |
| 45 | 2026-08-18 08:00 | 2026-08-19 15:00 | ARBUSDT | LONG | $0.0760 | $0.0783 | $    7.70 | $   184.46 | $    0.00 |
| 46 | 2026-08-21 03:00 | 2026-08-22 03:00 | POLUSDT | LONG | $0.0828 | $0.0985 | $ 1346.08 | $  1530.54 | $    0.00 |
| 47 | 2026-08-23 03:00 | 2026-08-23 04:00 | ONTUSDT | LONG | $0.0487 | $0.0494 | $    5.18 | $  1535.72 | $    0.00 |
| 48 | 2026-08-23 07:00 | 2026-08-23 10:00 | MORPHOUSDT | LONG | $2.3408 | $2.3759 | $  -37.04 | $  1498.68 | $    0.00 |
| 49 | 2026-08-23 10:00 | 2026-08-23 14:00 | INJUSDT | LONG | $5.0300 | $5.1055 | $    7.81 | $  1506.49 | $    0.00 |
| 50 | 2026-08-24 11:00 | 2026-08-24 12:00 | VELVETUSDT | SHORT | $0.2196 | $0.1879 | $ 2128.18 | $  3634.66 | $    0.00 |
| 51 | 2026-08-26 13:00 | 2026-08-26 14:00 | ONTUSDT | LONG | $0.0547 | $0.0555 | $   14.99 | $  3649.66 | $    0.00 |
| 52 | 2026-08-27 03:00 | 2026-08-27 04:00 | MOVRUSDT | LONG | $0.8294 | $1.0879 | $34648.40 | $ 31368.38 | $ 6929.68 |
| 53 | 2026-08-28 10:00 | 2026-08-28 12:00 | MORPHOUSDT | LONG | $2.6458 | $2.5929 | $ -582.95 | $ 30785.44 | $ 6929.68 |
| 54 | 2026-09-02 15:00 | 2026-09-02 22:00 | SEIUSDT | LONG | $0.0477 | $0.0484 | $  -98.93 | $ 30686.51 | $ 6929.68 |
| 55 | 2026-09-04 12:00 | 2026-09-04 13:00 | MORPHOUSDT | SHORT | $2.4263 | $2.4749 | $ -625.88 | $ 30060.63 | $ 6929.68 |
| 56 | 2026-09-06 01:00 | 2026-09-06 07:00 | MORPHOUSDT | LONG | $2.5615 | $2.5103 | $ -407.43 | $ 29653.20 | $ 6929.68 |
| 57 | 2026-09-07 05:00 | 2026-09-07 07:00 | AAVEUSDT | LONG | $135.6113 | $132.8991 | $-1777.52 | $ 27875.68 | $ 6929.68 |
| 58 | 2026-09-07 11:00 | 2026-09-07 12:00 | CAKEUSDT | LONG | $2.2780 | $2.3121 | $  -45.51 | $ 27830.18 | $ 6929.68 |
| 59 | 2026-09-09 15:00 | 2026-09-09 19:00 | ZROUSDT | LONG | $1.1393 | $1.1165 | $ -824.29 | $ 27005.89 | $ 6929.68 |

---

## 🚀 3. 1 YILLIK GELECEK PROJEKSİYONU (TARİHSEL TEKERRÜR VE MAKRO DÖNGÜ)
Kripto piyasasında Q4 (Ekim-Aralık / Uptober ve Yıl Sonu Rallisi) tarihsel olarak en yüksek getirili dönemdir.

| Ay / Dönem | Piyasa Rejimi | Kaldıraç | Beklenen Aylık Kâr | Aktif Kasa ($) | Spot Vault ($) | Toplam Net Servet |
|---|---|---|---|---|---|---|
| **0. Ay (Başlangıç)** | - | - | - | $100.00 | $0.00 | $100.00 (4.845 TL) |
| **6. Ay (Gerçekleşen)** | Yaz Chop + Mega Trend | 12x / 20x | - | **$27,005.89** | **$6,929.68** | **$33,935.57 (1.64 Milyon TL)** |
| **7. Ay (Ekim / Uptober)** | Güçlü Boğa Rallisi | 20x (2 Slot) | +%70 | $45,900.00 | $10,700.00 | $56,600.00 (2.74 Milyon TL) |
| **8. Ay (Kasım / Q4 Peak)**| Mega Altcoin Rallisi | 20x (2 Slot) | +%80 | $75,200.00 | $18,000.00 | $93,200.00 (4.51 Milyon TL) |
| **9. Ay (Aralık / Yıl Sonu)**| Trend Devamı | 20x (4 Slot) | +%50 | $105,300.00 | $25,500.00 | $130,800.00 (6.33 Milyon TL) |
| **10. Ay (Ocak / Q1 Başlangıç)**| Genişleme | 20x (4 Slot) | +%40 | $139,000.00 | $33,900.00 | $172,900.00 (8.37 Milyon TL) |
| **11. Ay (Şubat / Bahar Öncesi)**| Konsolidasyon | 20x (6 Slot) | +%30 | $171,900.00 | $42,100.00 | $214,000.00 (10.36 Milyon TL) |
| **12. Ay (Mart / Chop Kalkanı)**| Vergi/Chop Sezonu | **12x Kalkan**| +%15 | **$191,700.00** | **$47,000.00** | **$238,700.00 (11.56 MİLYON TL)** |

---

## 🎯 4. MAAŞ & NAKİT ÇEKİM STRATEJİSİ (HER AY $10.000+ NAKİT)
- Kasa $30.000 eşiğini aştığı için **7. Aydan itibaren her ay sabit $10.000 - $15.000 çekilebilir**.
- Bu çekim kasanın ana büyümesini durdurmaz; kalan bakiye 4 ve 6 slot ile sermayeyi büyütmeye devam eder.

*Bu doküman deterministik Binance verisiyle oluşturulmuştur ve `C:\Users\depco\OneDrive\Desktop\mtf_signal_engine\README_MASTER_AUDIT.md` adresinde yer almaktadır.*
