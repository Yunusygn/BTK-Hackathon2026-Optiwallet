# 🛒 OptiWallet — Kanıt Bazlı Türkçe Alışveriş Danışmanı

> **BTK Hackathon 2026** — 7 uzman AI agent + Reflexion auditor ile Türkiye e-ticaret pazarında akıllı, dürüst ve kişiselleştirilmiş alışveriş tavsiyesi.

![Status](https://img.shields.io/badge/status-MVP-success)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-15-black)
![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Pro-orange)

---

## 🎯 Problem

Türkiye'de online alışverişte 4 ana sorun var:

- 🚨 **Bilgi kirliliği**: Yüzlerce ürün arasından doğru seçim yapmak zor
- 💸 **Gizli maliyet**: 5 yıllık toplam sahip olma maliyeti (TCO) hiç hesaplanmıyor
- 🔍 **Servis riski**: Bazı markaların Türkiye'de servis ağı zayıf, kullanıcı bilmiyor
- 🎭 **Manipülatif öneriler**: AI'lar "her duruma her şeyi öner" diyerek satışı önceleyor

## 💡 Çözüm — OptiWallet

Türkiye perspektifli, **kanıt-bazlı**, **dürüst** ve **kişisel** bir AI danışman:

- 🤖 **7 Uzman Agent**: Her biri tek bir konuda uzman (Pazar, Araştırma, Finans, TCO, Strateji, Denetim)
- 🛡️ **Reflexion Auditor**: Kötü öneriyi REDDEDIP yeniden ürettiriyor
- 🌐 **Google Grounding**: Forum, şikayet sitesi, review verisi gerçek zamanlı
- 💰 **TCO Hesaplama**: 5 yıllık elektrik + aksesuar + servis maliyeti
- 🇹🇷 **Türkiye Bilinci**: "TCL global'de güzel ama Türkiye'de servis riskli" diyebilen sistem
- 🧠 **Akıllı Hafıza**: Anonim mod request-based, login mod DB-based

---

## 🏗️ Mimari

### 📊 Sistem Akışı

\`\`\`mermaid
graph TD
    A[👤 Kullanıcı Sorgusu] --> B{🎯 Consultant Agent<br/>Mode Dispatch}
    B -->|chat| C1[💬 Soru Sor<br/>bütçe, kategori]
    B -->|educational| C2[📚 Eğitim Cevabı<br/>OLED nedir, SSD vs.]
    B -->|off_topic| C3[🚫 Nazikçe Çek<br/>konuya yönlendir]
    B -->|ready| D[🛒 Market Agent<br/>Grounded Tarama]
    D --> E[🔬 Research Agent<br/>6 Boyut Puanlama]
    E --> F[💰 Finance Agent<br/>Kişisel / Generic]
    F --> G[⚡ TCO Agent<br/>5-Yıl Maliyet]
    G --> H[🧠 Strategy Agent<br/>2-Step JSON Sentez]
    H --> I{🛡️ Auditor Agent<br/>Reflexion Loop}
    I -->|❌ REJECT| H
    I -->|✅ APPROVE| J[🎯 Final Öneri<br/>Ürün + Plan + Uyarılar]

    style A fill:#3b82f6,color:#fff,stroke:#1e40af,stroke-width:2px
    style B fill:#8b5cf6,color:#fff,stroke:#6d28d9,stroke-width:2px
    style C1 fill:#a78bfa,color:#fff
    style C2 fill:#a78bfa,color:#fff
    style C3 fill:#a78bfa,color:#fff
    style D fill:#06b6d4,color:#fff
    style E fill:#06b6d4,color:#fff
    style F fill:#06b6d4,color:#fff
    style G fill:#06b6d4,color:#fff
    style H fill:#f59e0b,color:#fff
    style I fill:#ef4444,color:#fff
    style J fill:#10b981,color:#fff,stroke:#065f46,stroke-width:3px
\`\`\`

---
---

## ⭐ Öne Çıkan Özellikler

### 🤖 7 Uzman Agent

| Agent | Görev | Teknoloji |
|-------|-------|-----------|
| **Consultant** | Niyet anlama, mod yönlendirme | Gemini Pro |
| **Market** | E-ticaret pazar taraması | Pro + Google Grounding |
| **Research** | Forum/şikayet/review analizi | 2-step + Grounding |
| **Finance** | Kişisel finans değerlendirmesi | Pro + DB profil |
| **TCO** | 5 yıllık toplam maliyet | Pro + EPDK cache |
| **Strategy** | Tüm sinyalleri sentezle | 2-step JSON |
| **Auditor** | Reflexion kalite denetimi | Python + Pro |

### 🛡️ Reflexion Pattern

Auditor "kalite yetersiz" derse:
1. Strateji geri besleme alır
2. Tekrar üretim (max 2 deneme)
3. Hala kötüyse → kullanıcıya dürüstçe söyler

### 🧠 4 Akıllı Mod

- **Chat**: Soru sor (bütçe, kategori, kullanım)
- **Educational**: Eğitim cevabı (CPU nedir, OLED vs QLED)
- **Ready**: Full pipeline (ürün önerisi)
- **Off-topic**: Nazikçe konuya çek

---

## 🛠️ Teknoloji Stack

### Backend
- **Python 3.12** + **FastAPI**
- **LangGraph** (workflow orchestration)
- **Gemini 2.5 Pro** (AI)
- **PostgreSQL** (kalıcı veri)
- **Redis** (cache — opsiyonel)
- **SQLAlchemy 2.0** (async ORM)

### Frontend
- **Next.js 15** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Server-Sent Events** (streaming)
- **Lucide React** (ikonlar)

### DevOps
- **Docker Compose** (4 servis: backend, frontend, postgres, redis)

---

## 🚀 Kurulum

### Gereksinimler
- Docker Desktop
- Gemini API Key ([buradan al](https://aistudio.google.com/apikey))

### Adımlar

```bash
# 1. Repo'yu klonla
git clone https://github.com/Yunusygn/BTK-Hackathon2026-Optiwallet.git
cd BTK-Hackathon2026-Optiwallet

# 2. .env dosyasını oluştur (.env.example'dan kopyala)
cp .env.example .env

# 3. .env'i düzenle (GEMINI_API_KEY ekle)
# nano .env  veya  notepad .env

# 4. Docker compose ile başlat
docker-compose up -d

# 5. Tarayıcıda aç
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## 🎬 Demo Senaryoları

### Anonim Mod (Hızlı Test)
1. http://localhost:3000/chat
2. "40 bin TL bütçeyle 55 inç TV önerir misin? Ailecek izleyeceğiz."
3. ⏱️ 3-5 dakika bekle
4. Tam ürün önerisi + alternatifler + eylem planı

### Login Mod (Kişisel)
1. /login → demo bilgileriyle giriş
2. /chat → kişisel finans önerileri
3. Sidebar'da geçmiş sohbetler

---

## 🌟 Yenilikçi Özellikler

- **2-Step JSON Pipeline**: AI önce yaratıcı text üretir, sonra deterministik formatter JSON'a çevirir → validation fail %0
- **Persona-Bazlı Bütçe**: family_user %60-90, premium_user %80-100, budget_user %40-70
- **URL Garantisi**: AI URL üretmese bile, satıcıya özel arama URL'i (Trendyol, Hepsiburada, Amazon, N11, MediaMarkt, Teknosa, Vatan)
- **EPDK Cache**: Gerçek 2026 elektrik fiyatları (2.80-3.50 TL/kWh)
- **Energy Label Database**: TV/buzdolabı/çamaşır makinesi için A-G etiket → yıllık kWh
- **Anonim Hafıza**: DB kirlenmiyor, frontend state'te
- **Reflexion Loop**: Max 2 deneme, sonra dürüst "bekle" mesajı

---

## 📈 Manifesto

OptiWallet'ın değişmez ilkeleri:

1. **Strict Budget Respect**: Bütçeyi ASLA aşma
2. **Strict Honesty**: Alım kötüyse "bekle" de
3. **Türkiye Perspektifi**: Marka algı farkını dürüstçe söyle
4. **Empathy**: Sayıların ardındaki insanı gör
5. **Quality > Cheap**: En ucuzu değil, en uygunu öner

---

## 🗺️ Roadmap

### v1.0 (Mevcut — Hackathon)
- ✅ 7 Agent pipeline
- ✅ 4 mod (chat/educational/ready/off_topic)
- ✅ Login + anonim mod
- ✅ Geçmiş sohbetler + silme
- ✅ Reflexion auditor
- ✅ TCO cache + grounding

### v2.0 (Planlanan)
- ⏳ Favorileme + fiyat takibi
- ⏳ Fiyat düşüş alarmları (Celery)
- ⏳ Şifremi unuttum (Email entegrasyonu)
- ⏳ Akıllı kategori karşılaştırma
- ⏳ AI-üretilen ürün karşılaştırma tabloları
- ⏳ Çoklu dil desteği (EN, AR)

---

## 👤 Geliştirici

**Yunus Emre Yeğin**
- GitHub: [@Yunusygn](https://github.com/Yunusygn)
- Repo: [BTK-Hackathon2026-Optiwallet](https://github.com/Yunusygn/BTK-Hackathon2026-Optiwallet)

---

## 📄 Lisans

MIT License — Eğitim ve hackathon amaçlı geliştirilmiştir.

---

## 🙏 Teşekkürler

- **BTK Akademi** — Hackathon imkanı için
- **Google Gemini** — Güçlü AI API'si için
- **Open Source Community** — FastAPI, Next.js, LangGraph, ve nice araç için

---

**🎯 OptiWallet — Dürüst Alışveriş, Akıllı Tasarruf!** 🇹🇷


