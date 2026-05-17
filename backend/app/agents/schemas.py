"""
Agent Output Schemas — Pydantic V2 Validators.

Tüm agent çıktıları bu schema'lardan validate edilir.
Pattern: Domain-driven design + structured outputs.

İçindekiler:
- NeedsAnalysisOutput: ConsultantAgent kullanıyor (parsed_needs)
- SourceCitation: Tüm grounding citation'ları için ortak
- DimensionScore: 6-boyutlu MCDA için tek boyut skoru
- MultiCriteriaEvaluation: Bir marka için 6 boyutlu değerlendirme
- ResearchOutput: ResearchAgent v2 çıktısı (multi-criteria)
- AlternativeEvaluation: Tier 2 (özet)
- BrandMention: Tier 3 (sadece isim)
- ResearchOutputV3: ResearchAgent v3 (Hibrit Smart Filter)
- ClarificationOption / ClarificationQuestion: ConsultantAgent
- ConsultantOutput: ConsultantAgent çıktısı
- SellerInfo / PriceHistory / MarketProduct / MarketOutput: MarketAgent
- CreditCard / UserFinancialProfile: FinanceAgent input
- CashFlowAnalysis / PurchaseFeasibility / FinanceOutput: FinanceAgent
- TCOBreakdown / TCODataSource / TCOOutput: TCOAgent v2

Manifesto:
- Strict Budget Respect (kullanıcı sınırı kutsal)
- Multi-Criteria Decision Analysis (Consumer Reports standardı)
- Turkey + Global perspective (cross-cultural)
- Defense in Depth (Optional fields, defansif validators)
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
# Research Output (v2 — Multi-Criteria, legacy)
# ============================================================
class ResearchOutput(BaseModel):
    """
    ResearchAgent v2 — Multi-Criteria Decision Analysis çıktısı.

    Eski "top_brands" + "avoid_brands" listesi yerine artık
    her marka için detaylı 6-boyutlu değerlendirme yapılır.
    """

    consensus_summary: str = Field(
        ...,
        max_length=2500,
        description="2-4 cümlelik genel Türkçe özet",
    )

    evaluations: list[MultiCriteriaEvaluation] = Field(
        default_factory=list,
        description=(
            "Bütçe ve kriterlere uyan tüm markaların 6-boyutlu "
            "değerlendirmesi. İdeal sayı: 5-8 marka."
        ),
        max_length=15,
    )

    forum_quotes: list[dict] = Field(
        default_factory=list,
        description="Forum alıntıları: {source, quote, sentiment}",
        max_length=10,
    )

    category_insights: list[str] = Field(
        default_factory=list,
        description="Bu kategoride genel öğrenilen şeyler",
        max_length=10,
    )

    sources: list[SourceCitation] = Field(
        default_factory=list,
        max_length=30,
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Araştırmanın genel güvenilirliği",
    )


# ============================================================
# ResearchAgent v3 — Tiered Evaluation Schemas
# ============================================================
class AlternativeEvaluation(BaseModel):
    """
    Tier 2 - Özet değerlendirme (5-8. sıradaki markalar).
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
        description="Tek cümlelik özet",
    )

    why_not_top: str = Field(
        ...,
        max_length=300,
        description="Neden top 4'te değil",
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
        description="Kısa not",
    )


class ResearchOutputV3(BaseModel):
    """
    ResearchAgent v3 — Hibrit Smart Filter + Tournament çıktısı.

    3 katmanlı çıktı:
    - top_evaluations: 4 ana öneri (tam 6 boyut)
    - alternative_evaluations: 4 alternatif (özet)
    - market_overview: 7+ marka (sadece isim)
    """

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

    4 farklı interaction mode:
    - "ready": Tüm bilgiler net, pipeline başlayabilir
    - "clarification": 1-3 soru sorulması gerek
    - "educational": Kullanıcı bilgi istiyor
    - "category_selection": Kategori belirsiz, sor
    """

    ready_for_pipeline: bool = Field(
        ...,
        description="True = pipeline başlayabilir, False = clarification gerek",
    )

    parsed_needs: NeedsAnalysisOutput | None = Field(
        None,
        description="Net olarak çıkarılan ihtiyaçlar (ready=True ise)",
    )

    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        max_length=3,
        description="Sorulacak sorular (max 3, UX kuralı)",
    )

    educational_content: str | None = Field(
        None,
        max_length=3000,
        description="Bilgilendirme içeriği",
    )

    interaction_mode: str = Field(
        ...,
        description="ready | clarification | educational | category_selection",
    )

    message_to_user: str = Field(
        ...,
        max_length=2000,
        description="Kullanıcıya gösterilecek Türkçe mesaj",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Anlama güveni (Python iş kurallarıyla hesaplandı)",
    )


# ============================================================
# MarketAgent Schemas
# ============================================================
class SellerInfo(BaseModel):
    """Bir satıcının ürün için bilgileri."""

    seller_name: str = Field(..., max_length=100, description="Trendyol, Hepsiburada, vs.")
    price_try: float | None = Field(
        None,
        ge=0,
        description="Fiyat TRY (bilinmiyorsa None)",
    )
    url: str | None = Field(None, max_length=1000, description="Ürün sayfası URL")
    rating: float | None = Field(
        None,
        ge=0,
        le=10,
        description="Satıcı puanı 0-10 (Türk siteler 5 üzerinden, bazı yerler 10)",
    )
    delivery_info: str | None = Field(
        None,
        max_length=200,
        description="Teslimat süresi/durumu",
    )
    installment_info: str | None = Field(
        None,
        max_length=300,
        description="Taksit bilgisi (örn: '12 ay vade farksız')",
    )
    is_physical_store: bool = Field(
        False,
        description="Fiziksel mağazada da var mı",
    )


class PriceHistory(BaseModel):
    """Fiyat geçmişi bilgisi (varsa)."""

    current_price: float | None = Field(None, ge=0)
    last_30_days_avg: float | None = Field(None, ge=0)
    trend: str | None = Field(
        "stable",
        description="rising | falling | stable | unknown",
        max_length=20,
    )
    percent_change: float | None = Field(
        None,
        description="30 gün değişim yüzdesi",
    )


class MarketProduct(BaseModel):
    """Bir ürünün tam pazar analizi."""

    product_name: str = Field(..., max_length=200)
    brand: str | None = Field(None, max_length=100)

    best_price: float | None = Field(
        None,
        ge=0,
        description="En iyi fiyat (LLM bulamadıysa None)",
    )
    best_seller: SellerInfo | None = Field(
        None,
        description="En iyi satıcı (LLM bulamadıysa None)",
    )

    all_sellers: list[SellerInfo] = Field(
        default_factory=list,
        max_length=8,
        description="Tüm taranan satıcılar",
    )

    price_history: PriceHistory | None = Field(
        None,
        description="30 günlük fiyat trendi (varsa)",
    )

    campaign_alert: str | None = Field(
        None,
        max_length=500,
        description="Yaklaşan kampanya uyarısı",
    )

    stock_status: str = Field(
        "in_stock",
        description="in_stock | low_stock | out_of_stock",
        max_length=20,
    )

    is_within_budget: bool = Field(
        True,
        description="Kullanıcı bütçesi dahilinde mi",
    )


class MarketOutput(BaseModel):
    """MarketAgent çıktısı."""

    products: list[MarketProduct] = Field(
        default_factory=list,
        max_length=8,
        description="Top ürünler için pazar analizi",
    )

    market_summary: str = Field(
        default="Pazar analizi tamamlandı.",
        max_length=2000,
        description="Türkçe pazar özeti (genel trend, kampanyalar)",
    )

    budget_status: dict = Field(
        default_factory=dict,
        description="user_budget, in_budget_count, out_of_budget_count",
    )

    sources: list[SourceCitation] = Field(
        default_factory=list,
        max_length=20,
    )

    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================
# FinanceAgent Schemas
# ============================================================
class CreditCard(BaseModel):
    """Tek bir kredi kartı bilgisi."""

    bank_name: str = Field(..., max_length=50, description="Garanti, Akbank, vs.")
    card_name: str | None = Field(
        None,
        max_length=50,
        description="Bonus, Wings, Maximum, vs.",
    )
    credit_limit: float = Field(..., ge=0, description="Kart limiti TRY")
    current_debt: float = Field(
        0,
        ge=0,
        description="Mevcut borç TRY",
    )
    monthly_payment: float = Field(
        0,
        ge=0,
        description="Aylık asgari ödeme TRY",
    )


class UserFinancialProfile(BaseModel):
    """
    Kullanıcının finansal profili (KVKK uyumlu, opsiyonel).

    Hiçbir alan zorunlu değil — kullanıcı boş bırakırsa
    FinanceAgent tahminle çalışır.
    """

    monthly_income: float | None = Field(
        None,
        ge=0,
        description="Aylık net gelir TRY (opsiyonel)",
    )

    monthly_fixed_expenses: float | None = Field(
        None,
        ge=0,
        description="Sabit giderler (kira, fatura, vs.) TRY",
    )

    monthly_variable_expenses: float | None = Field(
        None,
        ge=0,
        description="Değişken giderler (yemek, ulaşım, eğlence) TRY",
    )

    current_savings: float | None = Field(
        None,
        ge=0,
        description="Birikim TRY",
    )

    credit_cards: list[CreditCard] = Field(
        default_factory=list,
        max_length=10,
        description="Kullanıcının kredi kartları",
    )

    consumer_loans_monthly: float = Field(
        0,
        ge=0,
        description="Mevcut tüketici kredisi aylık ödemesi TRY",
    )

    upcoming_expenses: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Yaklaşan giderler",
    )


class CashFlowAnalysis(BaseModel):
    """Cash flow analizi sonucu."""

    monthly_income: float = Field(..., ge=0)
    monthly_total_expenses: float = Field(..., ge=0)
    disposable_income: float = Field(..., description="Negative olabilir")

    current_debt_monthly: float = Field(
        0,
        ge=0,
        description="Mevcut aylık borç ödemeleri",
    )

    debt_to_income_ratio: float = Field(
        0,
        ge=0,
        description="Borç/gelir oranı (0.4+ tehlikeli)",
    )

    healthy_purchase_capacity: float = Field(
        ...,
        ge=0,
        description="Sağlıklı bir alıma ayırabileceği aylık miktar",
    )


class PurchaseFeasibility(BaseModel):
    """Bu alımı yapabilir mi analizi."""

    feasibility: str = Field(
        ...,
        description="rahat | zor | tehlikeli | imkansiz",
        max_length=20,
    )

    cash_purchase: dict = Field(
        ...,
        description="Peşin alım analizi",
    )

    installment_options: list[dict] = Field(
        default_factory=list,
        description="Taksit seçenekleri (3, 6, 9, 12 ay)",
    )

    recommendation: str = Field(
        ...,
        max_length=50,
        description="cash | installment_3 | installment_6 | installment_9 | installment_12 | delay",
    )

    reasoning: str = Field(
        ...,
        max_length=2000,
        description="Türkçe açıklama (3-5 cümle)",
    )


class FinanceOutput(BaseModel):
    """FinanceAgent çıktısı (Phase 1)."""

    profile_complete: bool = Field(
        ...,
        description="Kullanıcı yeterli finansal bilgi verdi mi",
    )

    cash_flow: CashFlowAnalysis | None = Field(
        None,
        description="Cash flow analizi (profile_complete=True ise)",
    )

    purchase_feasibility: PurchaseFeasibility | None = Field(
        None,
        description="Bu alım yapılabilir mi (profile_complete=True ise)",
    )

    coaching_message: str = Field(
        ...,
        max_length=3000,
        description="Türkçe finansal koçluk mesajı",
    )

    warnings: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Önemli uyarılar (acil fon, yüksek borç, vs.)",
    )

    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================
# TCOAgent v3 Schemas (Lean Honesty)
# ============================================================
class TCOBreakdown(BaseModel):
    """
    5-yıl Elektrik Maliyeti tahmini.

    LEAN HONESTY:
    - Sadece elektrik (bilimsel temelli)
    - Aralık gösterimi (min-max-avg)
    - Toplam tahmin YOK (kafa karıştırıcı)
    - Servis, aksesuar, ikinci el HESAPTA YOK (yalan riski)
    """

    purchase_price: float = Field(..., ge=0, description="Alış fiyatı TRY")

    energy_label: str = Field(
        "C",
        description="A, B, C, D, E, F, G veya 'unknown'",
        max_length=20,
    )

    # Yıllık tüketim ARALIĞI (tek rakam değil — EU standardı)
    annual_kwh_min: float = Field(
        ...,
        ge=0,
        description="EU standardı düşük sınır (yıllık kWh)",
    )
    annual_kwh_max: float = Field(
        ...,
        ge=0,
        description="EU standardı yüksek sınır (yıllık kWh)",
    )
    annual_kwh_avg: float = Field(
        ...,
        ge=0,
        description="Aralık ortalaması (yıllık kWh)",
    )

    kwh_price_try: float = Field(
        ...,
        ge=0,
        description="Türkiye güncel kWh fiyatı TRY",
    )

    # 5-yıl elektrik maliyeti ARALIĞI
    electricity_5yr_min: float = Field(
        ...,
        ge=0,
        description="5-yıl elektrik düşük tahmin",
    )
    electricity_5yr_max: float = Field(
        ...,
        ge=0,
        description="5-yıl elektrik yüksek tahmin",
    )
    electricity_5yr_avg: float = Field(
        ...,
        ge=0,
        description="5-yıl elektrik aralık ortalaması",
    )


class TCODataSource(BaseModel):
    """TCO hesaplamada kullanılan veri kaynakları (şeffaflık)."""

    energy_label_source: str = Field(
        "estimated",
        description="grounding | cache | estimated",
        max_length=20,
    )
    kwh_price_source: str = Field(
        "estimated",
        description="grounding | cache | estimated",
        max_length=20,
    )
    accessories_source: str = Field(
        "estimated",
        description="grounding | cache | estimated",
        max_length=20,
    )
    service_reliability_source: str = Field(
        "estimated",
        description="grounding | cache | estimated",
        max_length=20,
    )
    kwh_price_fetched_at: str | None = Field(
        None,
        description="ISO datetime kWh fiyatı çekildiği zaman",
    )


class AccessoryRecommendation(BaseModel):
    """Bir aksesuar önerisi (Grounding ile çekilebilir)."""

    name: str = Field(..., max_length=200, description="Aksesuar adı")
    price_range: str = Field(
        ...,
        max_length=100,
        description="Fiyat aralığı (örn: '1.500-3.000 TL')",
    )
    why_needed: str = Field(
        ...,
        max_length=500,
        description="Neden gerekli (kullanıcıya açıklama)",
    )
    importance: str = Field(
        "optional",
        description="essential | recommended | optional",
        max_length=20,
    )


class ServiceReliability(BaseModel):
    """Servis/arıza sıklığı bilgisi (Grounding ile)."""

    level: str = Field(
        ...,
        description="low | medium | high | unknown",
        max_length=20,
    )
    summary: str = Field(
        ...,
        max_length=800,
        description="Türkçe özet (tarih bilgisi dahil)",
    )
    common_issues: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Tespit edilen yaygın sorunlar (her madde tarih bilgili)",
    )
    active_complaints_last_12m: bool | None = Field(
        None,
        description="Son 12 ay içinde aktif şikayet var mı",
    )
    complaint_time_range: str | None = Field(
        None,
        max_length=50,
        description="Şikayet yıl aralığı (örn: '2022-2024')",
    )


class TCOOutput(BaseModel):
    """TCOAgent v3 çıktısı."""

    product_name: str = Field(..., max_length=200)
    breakdown: TCOBreakdown

    coaching_message: str = Field(
        ...,
        max_length=4000,
        description="Türkçe TCO açıklama mesajı",
    )

    accessories_recommended: list[AccessoryRecommendation] = Field(
        default_factory=list,
        max_length=10,
        description="Önerilen aksesuarlar (Grounding ile)",
    )

    service_reliability: ServiceReliability | None = Field(
        None,
        description="Servis/arıza sıklığı (Grounding ile)",
    )

    data_sources: TCODataSource = Field(
        default_factory=TCODataSource,
        description="Veri kaynakları (şeffaflık)",
    )

    sources: list[SourceCitation] = Field(
        default_factory=list,
        max_length=10,
    )

    confidence: float = Field(..., ge=0.0, le=1.0)

    # ============================================================
# StrategyAgent Schemas
# ============================================================
class StrategyRecommendedProduct(BaseModel):
    """Önerilen ana ürün."""

    name: str = Field(..., max_length=200)
    brand: str | None = Field(None, max_length=100)
    price_try: float | None = Field(None, ge=0, description="TRY fiyat")
    best_seller: str = Field(..., max_length=100)
    
    why_chosen: str = Field(
        ...,
        max_length=1500,
        description="Neden bu ürün seçildi (3-5 madde gerekçe)",
    )
    
    strengths: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Bu ürünün güçlü yönleri (özet)",
    )
    
    considerations: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Bilinmesi gereken durumlar",
    )


class StrategyAlternative(BaseModel):
    """Alternatif ürün önerisi."""

    name: str = Field(..., max_length=200)
    brand: str | None = Field(None, max_length=100)
    price_try: float | None = Field(None, ge=0, description="TRY fiyat (bilinmiyorsa None)")
    
    tier: str = Field(
        ...,
        description="budget | similar | premium",
        max_length=20,
    )
    
    one_line_reason: str = Field(
        ...,
        max_length=300,
        description="Tek cümlelik neden",
    )
    
    trade_off: str = Field(
        ...,
        max_length=500,
        description="Ne kazanırsın, ne kaybedersin",
    )


class StrategyActionStep(BaseModel):
    """Eylem planı adımı."""

    order: int = Field(..., ge=1, le=10)
    action: str = Field(..., max_length=300)
    why: str = Field(..., max_length=500, description="Bu adımın gerekçesi")
    priority: str = Field(
        "normal",
        description="critical | important | normal",
        max_length=20,
    )


class StrategyOutput(BaseModel):
    """StrategyAgent çıktısı — final sentez."""

    # Persona detection
    persona_detected: str = Field(
        ...,
        description="budget_conscious | quality_seeker | tech_enthusiast | family_user | general",
        max_length=50,
    )
    persona_reasoning: str = Field(
        ...,
        max_length=500,
        description="Bu persona neden tespit edildi",
    )

    # Ana tavsiye
    recommended_product: StrategyRecommendedProduct = Field(
        ...,
        description="Kullanıcı için en uygun ürün",
    )

    # Alternatifler
    alternatives: list[StrategyAlternative] = Field(
        default_factory=list,
        max_length=3,
        description="1-3 alternatif (ucuz, benzer, premium)",
    )

    # Eylem planı
    action_plan: list[StrategyActionStep] = Field(
        default_factory=list,
        max_length=7,
        description="3-7 adımlık eylem planı",
    )

    # Dikkat edilecekler
    warnings: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Önemli uyarılar (Finance + TCO uyarılarından sentez)",
    )

    # Final mesaj
    final_message: str = Field(
        ...,
        max_length=3000,
        description="Türkçe empatik sonuç mesajı (3-5 paragraf)",
    )

    # Karar matrisi (özet karşılaştırma)
    decision_matrix_summary: str = Field(
        ...,
        max_length=1000,
        description="Top 3 ürün için kısa karşılaştırma metni",
    )

    confidence: float = Field(..., ge=0.0, le=1.0)