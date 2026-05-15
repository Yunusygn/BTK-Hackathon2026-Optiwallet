"""
Question Bank — Kategori bazlı clarification soruları.

ConsultantAgent kullanıcıya soru sorarken bu bankayı kullanır.
Her kategori için 3-5 kritik soru tanımlı.

Pattern: Multiple choice + "Bilmiyorum" seçeneği.
Maksimum 3 soru sorulur (UX kuralı).
"""

from __future__ import annotations

from typing import Any


# ============================================================
# Question Bank — Kategori → Sorular
# ============================================================
QUESTION_BANK: dict[str, list[dict[str, Any]]] = {

    # ============================================================
    # TV
    # ============================================================
    "tv": [
        {
            "field": "budget_max",
            "question": "💰 Yaklaşık bütçen ne kadar?",
            "options": [
                {"label": "5-15K TL (giriş seviye)", "value": 12000},
                {"label": "15-25K TL (orta segment — en popüler)", "value": 22000},
                {"label": "25-50K TL (üst orta)", "value": 35000},
                {"label": "50K TL+ (premium)", "value": 75000},
                {"label": "Bilmiyorum, sen tahmin et", "value": None},
            ],
            "default_if_skip": 22000,
            "priority": 1,
        },
        {
            "field": "use_case",
            "question": "🎬 En çok ne için kullanacaksın?",
            "options": [
                {"label": "Ailecek film/dizi izleme", "value": "movie_family"},
                {"label": "Oyun (PS5, Xbox, PC)", "value": "gaming"},
                {"label": "Spor maçları", "value": "sports"},
                {"label": "Genel kullanım", "value": "general"},
                {"label": "Bilmiyorum", "value": "general"},
            ],
            "default_if_skip": "general",
            "priority": 2,
        },
        {
            "field": "size",
            "question": "📏 Ekran boyutu tercihin?",
            "options": [
                {"label": "43 inç (küçük oda)", "value": "43_inch"},
                {"label": "50 inç (orta)", "value": "50_inch"},
                {"label": "55 inç (en popüler)", "value": "55_inch"},
                {"label": "65 inç (geniş salon)", "value": "65_inch"},
                {"label": "75 inç+ (sinema gibi)", "value": "75_inch"},
                {"label": "Bilmiyorum, sen öner", "value": "55_inch"},
            ],
            "default_if_skip": "55_inch",
            "priority": 3,
        },
    ],

    # ============================================================
    # Laptop
    # ============================================================
    "laptop": [
        {
            "field": "budget_max",
            "question": "💰 Bütçen?",
            "options": [
                {"label": "10-20K TL (öğrenci/ofis)", "value": 18000},
                {"label": "20-35K TL (orta)", "value": 30000},
                {"label": "35-60K TL (gaming/iş)", "value": 50000},
                {"label": "60K TL+ (premium)", "value": 85000},
                {"label": "Bilmiyorum", "value": 30000},
            ],
            "default_if_skip": 30000,
            "priority": 1,
        },
        {
            "field": "use_case",
            "question": "💼 Kullanım amacı?",
            "options": [
                {"label": "Ofis/Ödev (Word, Excel)", "value": "office"},
                {"label": "Oyun (gaming)", "value": "gaming"},
                {"label": "Tasarım/Video (Photoshop, render)", "value": "creative"},
                {"label": "Hibrit (ofis + oyun)", "value": "hybrid"},
                {"label": "Programlama/Yazılım", "value": "development"},
                {"label": "Bilmiyorum", "value": "office"},
            ],
            "default_if_skip": "office",
            "priority": 2,
        },
        {
            "field": "portability",
            "question": "🎒 Taşınabilirlik önemli mi?",
            "options": [
                {"label": "Çok önemli (her gün taşıyacağım)", "value": "high"},
                {"label": "Orta (zaman zaman)", "value": "medium"},
                {"label": "Önemsiz (masada duracak)", "value": "low"},
                {"label": "Bilmiyorum", "value": "medium"},
            ],
            "default_if_skip": "medium",
            "priority": 3,
        },
    ],

    # ============================================================
    # Phone (Telefon)
    # ============================================================
    "phone": [
        {
            "field": "budget_max",
            "question": "💰 Bütçen?",
            "options": [
                {"label": "5-15K TL (giriş)", "value": 12000},
                {"label": "15-30K TL (orta)", "value": 25000},
                {"label": "30-50K TL (üst orta)", "value": 40000},
                {"label": "50K+ TL (flagship)", "value": 75000},
                {"label": "Bilmiyorum", "value": 25000},
            ],
            "default_if_skip": 25000,
            "priority": 1,
        },
        {
            "field": "use_case",
            "question": "📱 En çok ne için kullanacaksın?",
            "options": [
                {"label": "Sosyal medya + WhatsApp", "value": "social"},
                {"label": "Fotoğraf/Video çekimi", "value": "camera"},
                {"label": "Oyun (PUBG, Genshin, vs.)", "value": "gaming"},
                {"label": "İş/Profesyonel", "value": "business"},
                {"label": "Genel kullanım", "value": "general"},
                {"label": "Bilmiyorum", "value": "general"},
            ],
            "default_if_skip": "general",
            "priority": 2,
        },
        {
            "field": "os_preference",
            "question": "🤖 İşletim sistemi tercihin?",
            "options": [
                {"label": "Android", "value": "android"},
                {"label": "iOS (iPhone)", "value": "ios"},
                {"label": "Fark etmez", "value": "any"},
                {"label": "Bilmiyorum", "value": "any"},
            ],
            "default_if_skip": "any",
            "priority": 3,
        },
    ],

    # ============================================================
    # Default — Belirsiz kategori için
    # ============================================================
    "_default": [
        {
            "field": "category",
            "question": "🛒 Hangi kategoride ürün arıyorsun?",
            "options": [
                {"label": "TV", "value": "tv"},
                {"label": "Laptop", "value": "laptop"},
                {"label": "Telefon", "value": "phone"},
                {"label": "Kulaklık", "value": "headphones"},
                {"label": "Beyaz Eşya (buzdolabı, çamaşır)", "value": "appliance"},
                {"label": "Mobilya", "value": "furniture"},
                {"label": "Diğer (yaz)", "value": "other"},
            ],
            "default_if_skip": None,
            "priority": 1,
        },
    ],
}


# ============================================================
# Confidence Thresholds
# ============================================================
class ConfidenceThresholds:
    """
    Karar verme eşikleri.

    Pythonda kendi confidence hesabımızı kullanıyoruz:
    - Sadece kategori var:     0.40
    - Kategori + Use_case:     0.60
    - Kategori + Budget:       0.70
    - Hepsi var:               0.90+

    READY threshold yüksek tutuldu çünkü bütçesiz öneri olmaz.
    OptiWallet Manifesto: "Strict Budget Respect"
    """

    READY = 0.85          # Pipeline başlayabilir (tüm kritik info var)
    NEEDS_ONE_Q = 0.55    # 1 soru yeterli (bütçe veya use_case eksik)
    NEEDS_FEW_QS = 0.30   # 2-3 soru gerekli (birden fazla eksik)
    CATEGORY_UNKNOWN = 0.20  # Kategori belirsiz


# ============================================================
# Educational Content (Eğitim Modu)
# ============================================================
EDUCATIONAL_CONTENT: dict[str, str] = {
    "tv": """
TV satın alırken bakman gereken 6 ana kriter:

📺 1. EKRAN TEKNOLOJİSİ
   OLED > QLED > Mini-LED > LED
   • Film için: OLED en iyi (siyahlar mükemmel)
   • Bütçe için: QLED mantıklı (canlı renkler)

🎨 2. ÇÖZÜNÜRLÜK
   • 4K UHD: Standart (modern içerik için ideal)
   • 8K: Şu an gereksiz (içerik az)
   • Full HD: Eski, kaçın

🌈 3. HDR DESTEĞİ
   • HDR10+ ve Dolby Vision en iyi
   • Bütçeli modellerde sadece HDR10

⚡ 4. PANEL HIZI (Refresh Rate)
   • 60Hz: Genel kullanım yeterli
   • 120Hz: Oyun için kritik

🔊 5. SES KALİTESİ
   • TV hoparlörleri çoğu zaman zayıf
   • Soundbar ek bütçe gerek (1-3K)

🧠 6. SMART TV İŞLETİM SİSTEMİ
   • Google TV: En zengin (Samsung hariç)
   • Tizen: Samsung'un sistemi (akıcı)
   • WebOS: LG (basit ve hızlı)
""",

    "laptop": """
Laptop satın alırken bakman gereken 5 kritik özellik:

💻 1. İŞLEMCİ (CPU)
   • Intel Core i5/i7 12. nesil+ veya
   • AMD Ryzen 5/7 6000 serisi+
   • Apple M1/M2/M3 (Mac için)

🎮 2. EKRAN KARTI (GPU) — Oyun için kritik
   • NVIDIA RTX 4050: Giriş gaming
   • NVIDIA RTX 4060: Orta-üst gaming
   • Integrated (Intel/AMD): Ofis ve genel

💾 3. RAM
   • 8 GB: Minimum (ofis için)
   • 16 GB: Önerilen (gaming, hybrid)
   • 32 GB: Profesyonel (render, dev)

💿 4. DEPOLAMA (SSD)
   • 256 GB: Az (sadece OS)
   • 512 GB: İdeal (ortalama kullanıcı)
   • 1 TB+: Geniş kullanım

📺 5. EKRAN
   • Boyut: 14" (taşınabilir) - 17" (oyun)
   • Çözünürlük: Full HD yeterli, 2K-4K bonus
   • Yenileme: 60Hz genel, 144Hz oyun
""",

    "phone": """
Telefon satın alırken 5 ana kriter:

📱 1. İŞLEMCİ
   • Apple A17/A18: Premium (iPhone 15/16)
   • Snapdragon 8 Gen 3+: Android flagship
   • Mediatek Dimensity 9000+: Orta-üst
   • Snapdragon 7s: Orta segment

📷 2. KAMERA
   • Yüksek megapixel ≠ daha iyi
   • Sensör boyutu önemli
   • Optik zoom var mı?
   • Gece çekim performansı

🔋 3. PİL
   • 4000-5000 mAh: Standart
   • 5000+ mAh: Uzun ömür
   • Hızlı şarj (45W+) önemli

💾 4. RAM + DEPOLAMA
   • RAM: 8 GB minimum (2026 standart)
   • Depolama: 128 GB minimum, 256 GB ideal

🖥️ 5. EKRAN
   • OLED > LCD (renk + pil)
   • 120Hz yumuşaklık
   • Boyut: 6.1" (tek el) - 6.7" (büyük)
""",
}