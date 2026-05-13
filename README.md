# BTK-Hackathon2026-Optiwallet
# OptiWallet — Akıllı Alışveriş Danışmanı

> **BTK Hackathon 2026 — Google + BTK Akademi + Girişimcilik Vakfı**

OptiWallet, Türkiye'deki tüketicilerin alışveriş kararlarını kolaylaştıran **AI destekli akıllı alışveriş danışmanıdır**. Kullanıcı tek bir cümle yazar; OptiWallet piyasayı tarar, fiyatları karşılaştırır, bütçeyi analiz eder ve kişiselleştirilmiş tavsiyeyi gerekçeli olarak sunar.

---

## Problem

Türkiye'de bir ürün almak ortalama **45 dakika** sürüyor:
- 5 farklı sitede fiyat karşılaştırma
- Hangi kartla kaç taksit yapılacağını hesaplama
- Kupon ve indirimleri uygulama
- Bütçeye uyup uymadığını kontrol etme

Sonuçta yanlış karar verme ihtimali yüksek.

## Çözüm

Kullanıcı yazar: *"55 inç TV alacağım, 25 bin TL bütçem var, ailecek film izliyoruz"*

OptiWallet **10 saniyede** şunları yapar:
-  Forum, review ve YouTube'dan piyasa konsensüsü çıkarır
-  Trendyol, Hepsiburada, Amazon TR ve 40+ platformdan anlık fiyat çeker
-  Bütçeyi ve kart bilgilerini analiz eder
-  Kişisel tavsiyesini gerekçeli sunar
-  Her adımı denetler (Verifier + Auditor — Reflexion pattern)

---

## 7 Ajanlı AI Mimarisi

| Ajan | Görev | Gemini Özelliği |
|---|---|---|
| **Research** | Forum, review, video tarama | Google Grounding |
| **Needs Analysis** | Doğal dili teknik kritere çevirme | 1M context + JSON mode |
| **Market** | Anlık fiyat ve kupon | Google Grounding |
| **Finance** | Bütçe, kart, taksit | Function calling + Python tools |
| **Strategy** | Tüm verileri sentezleme | 1M context |
| **Verifier** | Faktüel doğrulama (link, fiyat, matematik) | Reflexion |
| **Auditor** | Mantıksal doğrulama (önyargı, tutarlılık) | Reflexion |

---

## Özellikler

### Sohbet Sistemi
- Doğal dil ile alışveriş danışmanlığı
- Streaming ajan akışı (canlı görselleştirme)
- Multi-turn conversation + memory
- Sınırsız sohbet, etiketleme, arama, export

### Multimodal Giriş
- Foto yükleme (mağaza etiketi OCR)
- Galeri / kamera erişimi
- Barkod ve QR kod tarama
- Sesli giriş (Gemini Live API)

### Mali Yönetim
- Bütçe takibi + kategori bazlı analiz
- Mali hedef projeksiyonu
- Kredi kartı optimizasyonu
- Mock banka entegrasyonu (8 banka simülatörü)
- Periyodik ödeme takibi

### Pazaryeri Desteği
- 40+ Featured platform: Trendyol, Hepsiburada, Amazon TR, N11, Vatan, Teknosa, Migros, Sahibinden vb.
- Sınırsız platform: Gemini Grounding ile Türkiye'deki tüm e-ticaret siteleri
- Fiyat geçmişi, sahte indirim tespiti, kupon doğrulama

### Bildirimler
- Fiyat düşüş alarmları
- Bütçe aşımı uyarıları
- Periyodik ödeme hatırlatmaları
- Push notification (PWA)

### Güvenlik
- Email + Google + Apple ile giriş
- 2FA (TOTP) + WebAuthn (passkey)
- JWT + refresh token rotasyonu
- AES-256 veri şifreleme
- KVKK uyumlu

---

## Teknoloji Stack

### Backend
- **Python 3.12** + FastAPI
- **LangGraph** + **LangChain** (7 ajanlı orkestrasyon)
- **Gemini SDK** (Google AI)
- **PostgreSQL 16** + **SQLAlchemy 2.0**
- **Redis 7** (cache + queue)
- **Celery** (background jobs)

### Frontend
- **Next.js 14** + **TypeScript**
- **Tailwind CSS** + **shadcn/ui**
- **PWA** (web + mobil tek seferde)
- **Zustand** (state) + **React Query** (server state)
- **Recharts** (grafikler) + **Framer Motion** (animasyon)

### DevOps
- **Docker Compose** (tek komutla ayağa kalkış)
- **GitHub Actions** (CI/CD)
- **Vercel** (frontend deploy) + **Railway** (backend deploy)

---

## Hızlı Başlangıç

### Ön Koşullar
- Docker Desktop
- Node.js 20+
- Python 3.12+
- Git

### Kurulum

```bash
# Repo'yu clone'la
git clone https://github.com/Yunusygn/BTK-Hackathon2026-Optiwallet.git
cd BTK-Hackathon2026-Optiwallet

# Environment dosyasını oluştur
cp .env.example .env
# .env içine Gemini API key'ini ekle

# Servisleri ayağa kaldır
docker-compose up -d

# Servislere eriş:
# Frontend:    http://localhost:3000
# Backend:     http://localhost:8000/docs
# Mock Bank:   http://localhost:8001/docs
# pgAdmin:     http://localhost:5050
```

---

## Proje Yapısı
BTK-Hackathon2026-Optiwallet/
├── backend/              # Ana FastAPI servisi (7 ajan)
│   ├── app/
│   │   ├── agents/       # 7 AI ajan
│   │   ├── tools/        # 11 araç (math, grounding, OCR vb.)
│   │   ├── graph/        # LangGraph orkestrasyon
│   │   ├── api/          # REST endpoints
│   │   ├── models/       # Database modelleri
│   │   └── core/         # Konfigürasyon, güvenlik
│   └── tests/
├── frontend/             # Next.js + PWA
│   ├── app/              # Sayfa routing (App Router)
│   ├── components/       # UI komponentleri
│   ├── lib/              # Yardımcı kütüphaneler
│   └── public/           # Statik dosyalar
├── mock-bank-api/        # Banka simülatörü (8 banka)
│   └── app/
├── docs/                 # Dokümantasyon
├── scripts/              # Yardımcı scriptler
└── docker-compose.yml    # Tüm servisleri ayağa kaldırma

---

## Demo

[Demo video buraya eklenecek]

---

## Takım

- **Yunus Emre Yeğin** — Full-stack & AI

---

## Lisans

MIT License — `LICENSE` dosyasına bakın.

---

## Teşekkürler

BTK Akademi, Google, ve Girişimcilik Vakfı'na bu hackathon için teşekkürler.

---

**OptiWallet — Bütçeni söyle, gerisini bana bırak. 🛒✨**