# 🎯 OptiWallet — Vizyon ve İlke Belgesi

> **Kişisel CFO + Alışveriş Danışmanı + Yaşam Stratejisti**  
> Bilinçli kararlar veren AI dostu.

---

## 🌟 Misyon

İnsanların alışveriş kararlarında **haftalarca süren araştırmayı dakikalara indirgemek**, **finansal sağlığını koruyarak** doğru ürünü, doğru zamanda, doğru ödeme planıyla almasına yardım etmek.

**Önemli:** Karar veren biz değiliz. **Karara YARDIM EDİYORUZ.** Son söz her zaman kullanıcının.

---

## 👤 Persona Hikayesi: Ahmet

Ahmet, üniversite öğrencisi. 40.000 TL bütçesi var, laptop arıyor.

> *"Üniversite ödevlerim ve arada oyun oynamak için 40.000 TL bütçeyle bir laptop arıyorum, ama teknik özelliklerden hiç anlamıyorum."*

### Manuel Alışveriş

- 3 gün araştırma yapar, kafası karışır
- Muhtemelen yanlış cihaz alır (çok ağır veya zayıf)
- En ucuzu bulduğunu sanır ama kampanyayı kaçırır
- Ay sonunda nakit sıkıntısı çeker
- 1 ay sonra pişman olur

### OptiWallet ile

- 30 saniyede ihtiyacı anlaşılır (LoL → hibrit segment)
- 6 boyutta marka değerlendirmesi (Türkiye + Global)
- 5 satıcıdan en iyi fiyat + güvenilirlik
- Cash flow analizi: "Haftaya kira + kredi kartı var, peşin zor"
- Akıllı taksit önerisi: "Garanti vade farksız 6 taksit"
- TCO hesabı: "5 yıllık toplam maliyet 45K (elektrik dahil)"
- **Sonuç:** İçi rahat alışveriş

---

## 🤖 7 Agent Mimarisi

### Hiyerarşi

```
👤 KULLANICI (CEO — En Üst Patron)
   ↑ Son söz, veto hakkı
   |
🎩 OPTIWALLET AI (Senior Manager Patron)
   ↑ Bilgi toplar, sentez yapar, önerir
   |
🛠️ 7 SPECIALIST AGENTS (Asistanlar)
```

### Agent Listesi

| # | Agent | Görev | Süre | LLM | Vision |
|---|-------|-------|------|-----|--------|
| 1 | **ConsultantAgent** | Anla, eksikse soru sor | 3-5s | Flash | ✅ |
| 2 | **ResearchAgent** | 6 boyutlu MCDA | 30-45s | Flash + Grounding | ❌ |
| 3 | **MarketAgent** | Fiyat + satıcı + kampanya | 20-30s | Flash + Grounding | ✅ |
| 4 | **FinanceAgent** | Cash flow + taksit | 5-10s | Flash + Tool | ❌ |
| 5 | **TCOAgent** | Toplam sahip olma maliyeti | 3-5s | Flash | ❌ |
| 6 | **StrategyAgent** | Sentez + final öneri | 5-10s | **Pro** | ❌ |
| 7 | **AuditorAgent** | Kalite + Reflexion | 3-5s | **Pro** | ✅ |

**Toplam süre: 70-110 saniye**

---

## 📊 ResearchAgent — 6 Boyutlu MCDA

Her marka/ürün **6 boyutta** değerlendirilir:

1. **Performance** — Görüntü, ses, hız, teknoloji
2. **Reliability** — 5+ yıl dayanıklılık
3. **Service & Support** — Türkiye servis ağı, parça
4. **Value for Money** — Fiyat/performans
5. **User Satisfaction** — Geniş kitle memnuniyeti
6. **Long-term Quality** — Uzun vadeli kalite

### Cross-Cultural Perspective

Her ürün **Türkiye + Global** perspektif farkıyla analiz edilir:

- **Beko Paradoxu:** Türkiye'de servis 10/10, global'de teknoloji 6/10
- **TCL Paradoxu:** Global'de "premium budget", Türkiye'de "Çin malı" algısı
- **Samsung Paradoxu:** Global'de elite, Türkiye'de aynı fiyata orta segment

---

## 📸 Visual Input (Multimodal)

Gemini'nin native multimodal yeteneği:

- 📷 **Mağaza fotoğrafı** → Ürün/marka tespit
- 🏷️ **Etiket fotoğrafı** → Spec okuma
- 🛏️ **Oda fotoğrafı** → Dekor uyumlu öneri
- 🆚 **2 ürün** → Side-by-side karşılaştırma

---

## 🛡️ Dürüstlük İlkeleri (10 Madde)

1. **Her İddia Kaynaklı** — Kaynaksız bilgi yok
2. **Belirsizlik Şeffaf** — "Bilmiyorum" demek yanlış cevaptan iyi
3. **Zaman Damgalı** — Fiyatlar tarihle belirtilir
4. **Tahmin Açık** — Varsayımlar görünür
5. **Finansal Tavsiye Yok** — Hisse, kripto, yatırım önerme
6. **Karar Kullanıcının** — Biz bilgi sunarız
7. **Hata İtirafı** — AuditorAgent yakalarsa düzeltiriz
8. **Sponsorlu İçerik Süzülür** — Reklam karışmaz
9. **Ürün Uydurma Yasak** — Hayali model önerilmez
10. **Math = Python** — Rakamsal doğruluk kod ile

---

## 🛡️ Strict Constraint Respect

Kullanıcının sınırlarına **MUTLAK SAYGI**:

| Sınır | Kural |
|-------|-------|
| **Bütçe (25K)** | 25K üzeri ürün gösterilmez; yoksa "yok" denilir |
| **Boyut (55 inç)** | Farklı boyut önerilmez, sorulur |
| **Özellik (4K must)** | 1080p ürün filtrelenir |
| **Marka kısıtı** | "X istemiyorum" denilen marka önerilmez |
| **Lokasyon** | Kullanıcı şehrinde bulunan ürün önceliği |

**Sınırı esnetmek için kullanıcının AÇIK ONAYI gerekir.**

---

## 🎯 Conversational Co-pilot — 3 Senaryo

### 1. Net İstek
```
👤 "55 inç TV, 25K bütçe, ailecek film"
🤖 Direkt 7-agent pipeline → öneri
```

### 2. Belirsiz İstek (Clarification)
```
👤 "TV almak istiyorum"
🤖 "Birkaç soru sorabilir miyim?
    □ Ekran boyutu?
    □ Bütçe aralığı?
    □ Kullanım amacı?"
```

### 3. Follow-up (Explainer)
```
👤 "Neden Samsung 3.?"
🤖 [Mevcut analizden 2-3 saniyede cevap, agent'lar tekrar çalışmaz]
```

---

## 📅 Hackathon Timeline

- ✅ **Gün 1-2:** Foundation (28 tablo + Docker + 7 agent iskelet)
- ✅ **Gün 3:** ResearchAgent v2 (Multi-Criteria + Grounding)
- 🔄 **Gün 4:** ConsultantAgent + Market + Finance + TCO + Strategy + Auditor
- 🔜 **Gün 5:** Frontend Chat UI + SSE Streaming
- 🔜 **Gün 6:** Visual Input + Explainer + Conversation State
- 🔜 **Gün 7:** Test + Demo Video + README + Slayt
- 🔜 **Gün 8:** TESLİM (19 Mayıs 23:59)

---

## 🏆 Jüri Kriterleri Hedefleri

| Kriter | Puan | Hedef | Strateji |
|--------|------|-------|----------|
| Kullanıcı Değeri | 20 | 18-20 | Gerçek soruna gerçek çözüm |
| Teknik Puan | 20 | 18-20 | 7 agent + LangGraph + MCDA |
| Performans/Doğruluk | 10 | 9-10 | Real data + Reflexion |
| Agentic Yapılar | 10 | 10 | Multi-agent + self-criticism |
| Yenilikçilik | 10 | 9-10 | Multimodal + 6-boyut + Patron+Asistan |
| Kullanıcı Dostu | 10 | 9-10 | Doğal konuşma + şeffaflık |
| Takım Çalışması | 10 | 8-9 | Clean commit history |
| Sunum | 10 | 9-10 | Ahmet hikayesi + demo video |

**Hedef: 90+ puan** 🎯

---

## 🚫 Asla Yapmayacağımız Şeyler

```
❌ Finansal yatırım tavsiyesi (hisse, kripto)
❌ Halüsinasyon (kaynaksız iddia)
❌ Bütçe ihlali (zorla pahalı ürün)
❌ Hayali model uydurma
❌ Sponsorlu içerik öne çıkarma
❌ Kullanıcı tercihini görmezden gelme
❌ "Bilmiyorum" demekten kaçınma
```

---

## 📚 Teknik Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Agent Framework:** LangGraph (state machine)
- **LLM:** Gemini 2.5 Flash + Gemini 2.5 Pro
- **Grounding:** Google Search via Gemini
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Frontend:** Next.js 15 + Tailwind + shadcn/ui
- **Streaming:** Server-Sent Events
- **Container:** Docker Compose
- **Mock Bank:** FastAPI service (Türk bankacılığı simülasyonu)

---

**Belge sahibi:** Yunus Emre Yeğin (@Yunusygn)  
**Proje:** OptiWallet  
**Yarışma:** BTK Hackathon 2026  
**Deadline:** 19 Mayıs 2026, 23:59