"""
Agent Output Schemas — Pydantic V2 Validators.

Tüm agent çıktıları bu schema'lardan validate edilir.
Pattern: Domain-driven design + structured outputs.

İçindekiler:
- NeedsAnalysisOutput: NeedsAnalysisAgent çıktısı (legacy, ConsultantAgent kullanıyor)
- SourceCitation: Tüm grounding citation'ları için ortak
- DimensionScore: 6-boyutlu MCDA için tek boyut skoru
- MultiCriteriaEvaluation: Bir marka için 6 boyutlu değerlendirme
- ResearchOutput: ResearchAgent v2 çıktısı (multi-criteria)
- ClarificationOption: Multiple choice soru seçeneği
- ClarificationQuestion: Kullanıcıya sorulacak soru
- ConsultantOutput: ConsultantAgent çıktısı

Manifesto:
- Strict Budget Respect (kullanıcı sınırı kutsal)
- Multi-Criteria Decision Analysis (Consumer Reports standardı)
- Turkey + Global perspective (cross-cultural)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================
# NeedsAnalysis Output (Legacy + ConsultantAgent'da kullanılıyor)
# ============================================================
class NeedsAnalysisOutput(BaseModel):
    """
    Kullanıcının yapılandırılmış ihtiyaçları.

    Bu schema ConsultantAgent tarafından doldurulur ve
    sonraki agent'lar (Research, Market, Finance) tarafından kullanılır.
    """

    product_category: str = Field(
        ...,
        description="Genel ürün kategorisi (örn: tv, laptop, phone)",
        max_length=100,
    )
    product_subcategory: str | None = Field(
        None,
        description="Alt kategori (örn: smart_tv, gaming_laptop)",
        max_length=100,
    )
    must_have_features: list[str] = Field(
        default_factory=list,
        description="Olmazsa olmaz özellikler (snake_case)",
        max_length=20,
    )
    nice_to_have_features: list[str] = Field(
        default_factory=list,
        description="Olursa iyi olur özellikler",
        max_length=20,
    )
    budget_min: float | None = Field(None, description="Min bütçe", ge=0)
    budget_max: float | None = Field(None, description="Max bütçe", ge=0)
    budget_currency: str = Field("TRY", description="Para birimi", max_length=3)
    use_case: str | None = Field(
        None,
        max_length=500,
        description="Kullanım amacı (snake_case)",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================
# Source Citation (Common — used in multiple places)
# ============================================================
class SourceCitation(BaseModel):
    """
    Tek bir kaynak referansı.

    Gemini Grounding metadata'sından çıkarılır.
    Halüsinasyon yok — sadece gerçek web URL'leri.
    """

    title: str = Field(..., max_length=300)
    url: str = Field(..., max_length=1000)
    source_type: str = Field(
        "web",
        description="forum | review | video | blog | ecommerce | web",
        max_length=30,
    )
    snippet: str | None = Field(None, max_length=500)


# ============================================================
# Multi-Criteria Dimension Score
# ============================================================
class DimensionScore(BaseModel):
    """
    Tek bir boyutun (dimension) skoru.

    Her boyut için:
    - score: 0-10 arası numeric değer
    - confidence: skora ne kadar güvendiğimiz (kaynak sayısı, vs.)
    - evidence: bu skoru destekleyen 2-3 alıntı/gözlem
    - source_count: kaç kaynaktan ortaya çıktı

    Şeffaflık için: kullanıcı her skorun nereden geldiğini görür.
    """

    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Boyut skoru (0=çok kötü, 10=mükemmel)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Bu skora güven (0=az kaynak, 1=çok kaynak)",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Bu skoru destekleyen alıntılar/gözlemler",
        max_length=5,
    )
    source_count: int = Field(
        0,
        ge=0,
        description="Bu boyut için kaç kaynak tarandı",
    )


# ============================================================
# Multi-Dimensional Evaluation (per brand/product)
# ============================================================
class MultiCriteriaEvaluation(BaseModel):
    """
    Bir marka/ürün için 6 boyutlu değerlendirme.

    Consumer Reports + Wirecutter + akademik MCDA standardı.

    Boyutlar:
    1. Performance: Görüntü, ses, hız, teknoloji
    2. Reliability: 5+ yıl dayanıklılık
    3. Service & Support: Türkiye servis ağı, parça
    4. Value for Money: Fiyat/performans
    5. User Satisfaction: Geniş kitle memnuniyeti
    6. Long-term Quality: Uzun vadeli kalite

    Cross-cultural: Türkiye + Global perspektif ayrı tutulur.
    Beko paradoxu örneği: Türkiye'de servis 10, global'de tech 6.
    """

    # Identity
    name: str = Field(..., max_length=200, description="Marka veya model adı")
    brand: str | None = Field(None, max_length=100)

    # 6 Boyut
    performance: DimensionScore = Field(
        ...,
        description="Performans: Görüntü, ses, hız, teknoloji",
    )
    reliability: DimensionScore = Field(
        ...,
        description="Güvenilirlik: 5+ yıl sonra hâlâ çalışır mı?",
    )
    service_support: DimensionScore = Field(
        ...,
        description="Servis & Destek: Türkiye'de servis ağı, parça",
    )
    value_for_money: DimensionScore = Field(
        ...,
        description="Fiyat/Performans: Bu paraya değer mi?",
    )
    user_satisfaction: DimensionScore = Field(
        ...,
        description="Kullanıcı Memnuniyeti: Geniş kitle ne diyor",
    )
    long_term_quality: DimensionScore = Field(
        ...,
        description="Uzun Vadeli Kalite: 'X yıldır kullanıyorum'",
    )

    # Cross-cultural perspective
    turkey_perspective: str = Field(
        ...,
        max_length=1000,
        description="Türkiye'deki algı (Türk forumları, e-ticaret)",
    )
    global_perspective: str = Field(
        ...,
        max_length=1000,
        description="Global algı (RTINGS, TechRadar, vs.)",
    )

    # Strengths & Cautions
    strengths: list[str] = Field(
        default_factory=list,
        description="Güçlü yönler",
        max_length=10,
    )
    cautions: list[str] = Field(
        default_factory=list,
        description="Dikkat edilmesi gerekenler",
        max_length=10,
    )

    # Price info (Strict Budget Constraint için)
    estimated_price_try: float | None = Field(
        None,
        ge=0,
        description="Tahmini TRY fiyatı (MarketAgent gerçek fiyatla doğrular)",
    )
    is_within_budget: bool | None = Field(
        None,
        description="Kullanıcı bütçesi dahilinde mi (Strict Budget Constraint)",
    )

    # Overall verdict
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Ağırlıksız ortalama (kullanıcı persona'sıyla yeniden hesaplanır)",
    )


# ============================================================
# Research Output (v2 — Multi-Criteria)
# ============================================================
class ResearchOutput(BaseModel):
    """
    ResearchAgent v2 — Multi-Criteria Decision Analysis çıktısı.

    Eski "top_brands" + "avoid_brands" listesi yerine artık
    her marka için detaylı 6-boyutlu değerlendirme yapılır.

    Esnek değerlendirme sayısı: 0-15 marka.
    - Hiç ürün yoksa boş array (bütçede yok demek)
    - Bütçeye uyan markaları analiz eder
    - Kalite > Sayı felsefesi (genelde 3-8 ideal)
    """

    # Genel özet
    consensus_summary: str = Field(
        ...,
        max_length=2500,
        description="2-4 cümlelik genel Türkçe özet",
    )

    # Çok boyutlu marka/model değerlendirmeleri
    evaluations: list[MultiCriteriaEvaluation] = Field(
        default_factory=list,
        description=(
            "Bütçe ve kriterlere uyan tüm markaların 6-boyutlu "
            "değerlendirmesi. İdeal sayı: 5-8 marka. "
            "Az marka kullanıcı için zayıf, çok marka analiz felci yaratır."
        ),
        max_length=15,
    )

    # Forum gerçek alıntıları (kullanıcı için şeffaflık)
    forum_quotes: list[dict] = Field(
        default_factory=list,
        description="Forum alıntıları: {source, quote, sentiment}",
        max_length=10,
    )

    # Pazar genel notları (kategori bazında)
    category_insights: list[str] = Field(
        default_factory=list,
        description="Bu kategoride genel öğrenilen şeyler",
        max_length=10,
    )

    # Kaynaklar (Grounding metadata'dan)
    sources: list[SourceCitation] = Field(
        default_factory=list,
        max_length=30,
    )

    # Overall confidence
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Araştırmanın genel güvenilirliği",
    )

    # NOT: Bütçede hiç ürün yoksa evaluations boş olabilir,
    # bu geçerli bir durum — sistem "yok" diyebilmeli.
    # Eskiden "en az 1" zorunluluğu vardı, kaldırıldı.


# ============================================================
# ConsultantAgent Schemas
# ============================================================
class ClarificationOption(BaseModel):
    """Multiple choice soru seçeneği."""

    label: str = Field(
        ...,
        max_length=100,
        description="Görünen yazı (UI'da gösterilir)",
    )
    value: str | float | None = Field(
        None,
        description="İçeride kullanılacak değer (LLM'e gönderilir)",
    )


class ClarificationQuestion(BaseModel):
    """
    Kullanıcıya sorulacak clarification sorusu.

    Pattern: Multiple choice + "Bilmiyorum" seçeneği.
    UX kural: max 3 soru bir seferde (kullanıcı yorulmasın).
    """

    field: str = Field(
        ...,
        max_length=50,
        description="Hangi field için (budget_max, use_case, vs.)",
    )
    question: str = Field(
        ...,
        max_length=500,
        description="Türkçe soru metni",
    )
    options: list[ClarificationOption] = Field(
        default_factory=list,
        max_length=8,
        description="Multiple choice seçenekler",
    )
    allow_skip: bool = Field(
        True,
        description="Kullanıcı 'bilmiyorum' diyebilir mi?",
    )
    priority: int = Field(
        1,
        ge=1,
        le=10,
        description="1 = en önemli, 10 = en az önemli",
    )


class ConsultantOutput(BaseModel):
    """
    ConsultantAgent çıktısı.

    3 farklı interaction mode:
    - "ready": Tüm bilgiler net, pipeline başlayabilir
    - "clarification": 1-3 soru sorulması gerek
    - "educational": Kullanıcı bilgi istiyor (özellik anlatımı)
    - "category_selection": Kategori belirsiz, sor

    OptiWallet Manifesto:
    - Strict Budget Respect: Bütçe yoksa hazır deme
    - Progressive Conversation: Max 3 soru
    - Karar kullanıcının: Biz yardım ederiz, dayatmayız
    """

    # Karar
    ready_for_pipeline: bool = Field(
        ...,
        description="True = pipeline başlayabilir, False = clarification gerek",
    )

    # Parsed needs (sadece ready=True ise dolu)
    parsed_needs: NeedsAnalysisOutput | None = Field(
        None,
        description="Net olarak çıkarılan ihtiyaçlar (ready=True ise)",
    )

    # Clarification (eğer gerek varsa)
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        max_length=3,
        description="Sorulacak sorular (max 3, UX kuralı)",
    )

    # Eğitim modu (kullanıcı bilgi istiyorsa)
    educational_content: str | None = Field(
        None,
        max_length=3000,
        description="Bilgilendirme içeriği (TV özellikleri, vs.)",
    )

    # Mod
    interaction_mode: str = Field(
        ...,
        description="ready | clarification | educational | category_selection",
    )

    # Mesaj kullanıcıya
    message_to_user: str = Field(
        ...,
        max_length=2000,
        description="Kullanıcıya gösterilecek Türkçe mesaj",
    )

    # Confidence
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Anlama güveni (kendi iş kurallarımızla hesaplandı)",
    )

# ============================================================
# ResearchAgent v3 — Tiered Evaluation Schemas
# ============================================================

class AlternativeEvaluation(BaseModel):
    """
    Tier 2 - Özet değerlendirme (5-8. sıradaki markalar).

    Top 4'e giremedi ama bütçede ve kriterlere uyuyor.
    Kullanıcıya alternatif olarak sunulur.
    """

    name: str = Field(..., max_length=200, description="Marka veya model adı")
    brand: str | None = Field(None, max_length=100)

    overall_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Tahmini genel skor (0-10)",
    )

    one_line_summary: str = Field(
        ...,
        max_length=300,
        description="Tek cümlelik özet ('Servis güçlü ama tech orta')",
    )

    why_not_top: str = Field(
        ...,
        max_length=300,
        description="Neden top 4'te değil ('Görüntü kalitesi düşük')",
    )

    estimated_price_try: float | None = Field(
        None,
        ge=0,
        description="Tahmini fiyat TRY",
    )
    is_within_budget: bool | None = Field(
        None,
        description="Bütçe dahilinde mi",
    )


class BrandMention(BaseModel):
    """
    Tier 3 - Sadece bahsetme (9+ markalar).

    Pazarda var ama önerilen liste dışında.
    Şeffaflık için sadece adı + tek kelime durumu.
    """

    name: str = Field(..., max_length=200)
    status: str = Field(
        ...,
        max_length=50,
        description="premium | budget | out_of_budget | niche | unavailable",
    )
    note: str = Field(
        ...,
        max_length=500,
        description="Kısa not ('Bütçe üstü 32K' veya 'Çok yeni, az veri')",
    )


class ResearchOutputV3(BaseModel):
    """
    ResearchAgent v3 — Hibrit Smart Filter + Tournament çıktısı.

    3 katmanlı çıktı:
    - top_evaluations: 4 ana öneri (tam 6 boyut)
    - alternative_evaluations: 4 alternatif (özet)
    - market_overview: 7+ marka (sadece isim)

    Total ürün gösterimi: 15+ marka (şeffaflık)
    """

    # Genel özet
    consensus_summary: str = Field(
        ...,
        max_length=2500,
        description="Türkçe pazar özeti",
    )

    # 🥇 TIER 1: Top 4 - Tam 6 boyut MCDA
    top_evaluations: list[MultiCriteriaEvaluation] = Field(
        default_factory=list,
        description="Top 4 marka - tam 6 boyut analizi",
        max_length=4,
    )

    # 🥈 TIER 2: 5-8 - Alternatifler (özet)
    alternative_evaluations: list[AlternativeEvaluation] = Field(
        default_factory=list,
        description="Alternatifler (5-8. sıra) - özet bilgi",
        max_length=6,
    )

    # 🥉 TIER 3: 9+ - Pazardaki diğer markalar
    market_overview: list[BrandMention] = Field(
        default_factory=list,
        description="Pazardaki diğer markalar (sadece isim)",
        max_length=15,
    )

    # Forum & insights
    forum_quotes: list[dict] = Field(
        default_factory=list,
        description="Forum alıntıları",
        max_length=10,
    )

    category_insights: list[str] = Field(
        default_factory=list,
        description="Kategori içgörüleri",
        max_length=10,
    )

    sources: list[SourceCitation] = Field(
        default_factory=list,
        max_length=30,
    )

    # Strict Budget Constraint feedback
    total_brands_scanned: int = Field(
        0,
        ge=0,
        description="Aşama 1'de bulunan toplam marka sayısı",
    )
    brands_in_budget: int = Field(
        0,
        ge=0,
        description="Bütçeye giren marka sayısı",
    )

    confidence: float = Field(..., ge=0.0, le=1.0)