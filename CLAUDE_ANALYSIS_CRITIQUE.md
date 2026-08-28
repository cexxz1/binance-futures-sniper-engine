# CLAUDE RAPORU ELEŞTİRİSİ & GETİRİ DÜŞÜŞÜNÜN MÜHENDİSLİK ANALİZİ

> **Tarih:** 2026-08-27  
> **Konu:** Claude'un teorik önerilerinin asimetrik trend stratejisinde getiriyi neden 655.000$'dan 1.472$'a düşürdüğü analizi.

---

### 1. Claude'un Önerisi Ne İdi?
Claude, kurumsal risk yönetimi (Geleneksel Fon Yönetimi) bakış açısıyla sisteme 2 katı kural eklenmesini önerdi:
1. **Piyasa Rejimi (BTC Trend) Filtresi:** Altcoinlerde long açmadan önce Bitcoin'in (BTCUSDT) saatlik grafikte mutlaka boğa trendinde (`EMA9 > EMA21`) olmasını şart koştu.
2. **Devre Kesici (Circuit Breaker):** Günlük %10 kayıp veya 3 ardışık stop olduğunda sistemi 24 saatliğine tamamen dondurmayı (işlem açmayı durdurmayı) önerdi.

---

### 2. Bu İki Kural Neden Getiriyi Yok Etti?

#### A. Kripto Gerçeği: Altcoin Rallileri BTC Yatay/Düşerken Olur!
* Kripto para piyasasında **"Altcoin Season / Asimetrik Ralliler"** genellikle Bitcoin yatay bağladığında veya hafif geri çekildiğinde yaşanır.
* Claude'un BTC filtresi yüzünden bot, **MOVR (+%34 koşusu) ve ONT (+%32 koşusu)** sinyallerini *"BTC o an 1 saatlikte yükselmiyor"* diyerek engelledi.
* Sadece bu iki işlemin engellenmesi tek başına **+598.000$'lık kârın çöpe gitmesine** yol açtı.

#### B. Devre Kesici Paradoksu (Bileşik Getirinin Önünü Kesmek):
* Bizim stratejimizde **Zırhlı %2.0 Stop Loss** zaten vardır. Kötü bir işlemde bakiye sadece %2-3 erir, likidasyon riski yaşanmaz.
* 26 Ağustos'ta ZEC işleminde normal %2'lik korumalı stop vurulduğunda Claude'un devre kesicisi sistemi 24 saat kilitledi.
* Sistem kilitli olduğu için sadece 4 saat sonra başlayan ve 120.000$'lık kasayı **655.000$'a fırlatan dev MOVR patlamasına GİREMEDİ.**

---

### 3. Doğru Mühendislik Kararı (Hermes Sentezi):
* **Komisyonlar & Fonlama Ücretleri:** Claude haklıydı; Taker komisyonu (%0.10) ve 8 saatlik fonlama maliyetleri eklenmeliydi. Bunları ekledik (kârı 737k$'dan 655k$'a çekti, sistem sapasağlam çalışıyor).
* **Filtreler & Devre Kesici:** Altcoinlerin kendi hacim patlamasına güvenilmeli; BTC'ye aşırı bağımlı katı filtreler ve botu günlerce kilitleyen devre kesiciler kaldırılmalıdır.
