import urllib.request, json, time, math

# ==============================================================================
# LEVERAGE & RISK OPTIMIZER ENGINE (Kaldıraç ve Risk Ölçüm Motoru)
# ==============================================================================

def calculate_optimal_leverage(atr_pct: float, vol_ratio: float, rsi: float, min_lev: int = 10, max_lev: int = 25) -> int:
    """
    En iyi kaldıracı otomatik ölçen algoritma:
    1. Volatilite (ATR %) ne kadar düşükse, likidasyon mesafesi o kadar uzaktır -> Kaldıraç artırılabilir.
    2. Hacim (Vol Ratio) ve RSI ne kadar güçlüyse, kırılım momentumu o kadar serttir -> Kaldıraç artırılabilir.
    3. Asla min_lev (10x) altına inmez ve max_lev (25x) üstüne çıkmaz.
    """
    # Temel taban: 10x
    if atr_pct <= 1.5 and vol_ratio >= 2.0 and rsi >= 60:
        return 25  # Düşük oynaklık + Devasa Hacim Sıkışması
    elif atr_pct <= 2.2 and vol_ratio >= 1.6 and rsi >= 56:
        return 18  # Güçlü Boğa Trendi
    elif atr_pct <= 3.2:
        return 14  # Standart Trend
    else:
        return 10  # Yüksek Volatilite Güvenlik Modu (Taban 10x)

def calculate_liquidation_price(entry_price: float, leverage: int, mmr: float = 0.005) -> float:
    """
    Binance Vadeli İşlemler Isolated Likidasyon Fiyatı Formülü (LONG).
    """
    return entry_price * (1.0 - (1.0 / leverage) + mmr)

def calculate_hard_sl_price(entry_price: float, sl_pct: float = 0.02) -> float:
    """
    Korumalı Sabit %2.0 Zarar Kes Fiyatı.
    """
    return entry_price * (1.0 - sl_pct)

# ==============================================================================
# Self-Check Testleri
# ==============================================================================
if __name__ == '__main__':
    # Test 1: Sıkışmış Parite (Düşük ATR, Yüksek Hacim) -> 25x seçmeli
    lev1 = calculate_optimal_leverage(atr_pct=1.2, vol_ratio=2.4, rsi=65)
    assert lev1 == 25, f"Hata: 25x bekleniyordu, {lev1}x geldi"
    
    # Test 2: Yüksek Oynaklık (Yüksek ATR) -> Güvenli 10x seçmeli
    lev2 = calculate_optimal_leverage(atr_pct=4.5, vol_ratio=1.5, rsi=55)
    assert lev2 == 10, f"Hata: 10x bekleniyordu, {lev2}x geldi"
    
    # Test 3: Likidasyon vs SL Güvenlik Mesafesi Doğrulaması
    entry = 100.0
    liq_18x = calculate_liquidation_price(entry, 18)
    sl_fixed = calculate_hard_sl_price(entry, 0.02)
    assert sl_fixed > liq_18x, "Güvenlik Hatası: SL Likidasyonun altında kalamaz!"
    
    print("[OK] Kaldirac Olcum Motoru ve Guvenlik Fonksiyonlari %100 Dogrulandi.")
