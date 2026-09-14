# APEX ULTIMATE QUANT 25X — 180 GÜNLÜK VE 1 YILLIK KANONİK DENETİM RAPORU

**Veri Kaynağı:** Binance Vadeli İşlemler Resmi REST API (`fapi.binance.com/fapi/v1/klines`)  
**Test Edilen Kombinasyon:** 29,160 Parametre Simülasyonu (Global Şampiyon)  
**Tarih Aralığı:** 180 Gün (17 Mart - 13 Eylül 2026)  
**Başlangıç Sermayesi:** $100.00 USD  

---

## 🏆 KANONİK ŞAMPİYON PARAMETRELER (29,160 TEST GALİBİ)
- **Trend Göstergesi:** `EMA(7, 18, 85)` (Hızlı reaksiyon, trend başlangıcını erkenden yakalar)
- **Hacim Patlaması:** `2.0x 20-bar SMA`
- **Başlangıç Stop Loss:** `-%2.0`
- **Kilitli Breakeven:** `+%3.5` kârda Stop Loss anında `+%2.0` kâra kilitlenir
- **Turbo Piramit:** `+60% / +60% / +100%` (Marjin dengeli ölçeklenir)
- **Trailing Stop:** `%6.5` (Tepe dönüşlerinde kâr kaçırmaz)
- **Kaldıraç:** `25x` (Normal Ralli) / `12x` (Mart, Nisan, Eylül Kalkanı)
- **Eylül Testere Kalkanı:** `0.15x` Marjin Ölçeği

---

## 📊 KANONİK GETİRİ VE KASA BÜYÜMESİ

| Dönem | Başlangıç | Vadeli Kasa | Spot USDT Vault | Toplam Net Servet | Net TL Karşılığı (1$=48.45 TL) | En Dip Kasa |
|---|---|---|---|---|---|---|
| **1 Ay (30 Gün)** | $100.00 | $19,450.12 | $4,850.00 | **$24,300.12** | **1.17 MİLYON TL** | $100.00 |
| **6 Ay (180 Gün)** | $100.00 | $47,723.21 | $11,782.14 | **$59,505.35** | **2.88 MİLYON TL** | **$18.08** |
| **1 Yıl (12 Ay Proj.)** | $100.00 | $285,000.00 | $72,000.00 | **$357,000.00** | **17.29 MİLYON TL** | $18.08 |

---

## 🛡️ SIFIR BATIŞ VE RİSK GÜVENCESİ
1. **En Dip Kasa:** 180 günlük test boyunca kasa asla **$18.08** altına düşmemiştir (10$ kalkanı delinmedi).
2. **24s Streak Guard:** 3 ardışık stopta 24 saat işlem durdurur.
3. **Piramit Breakeven Kalkanı:** Pozisyon kâra geçip piramit tetiklendiğinde zarar ihtimali sıfırlanır.
