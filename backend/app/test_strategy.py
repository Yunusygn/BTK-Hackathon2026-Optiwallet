"""StrategyAgent test — 5 agent verisi sentez."""

from __future__ import annotations

import asyncio
import time
import uuid

from app.agents.strategy import StrategyAgent
from app.agents.workflow import create_initial_state


async def test_with_full_data():
    """Tüm 5 agent verisiyle sentez testi."""
    print("=" * 80)
    print("🧪 STRATEGY AGENT TEST — Full Data")
    print("=" * 80)

    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query="55 inç akıllı TV, 40K bütçe, ailecek film izleyeceğiz",
    )

    state["user_context"] = {
        "financial_profile": {
            "monthly_income": 35000,
            "monthly_fixed_expenses": 12000,
            "monthly_variable_expenses": 6500,
            "current_savings": 50000,
            "credit_cards": [
                {
                    "bank_name": "Garanti",
                    "card_name": "Bonus",
                    "credit_limit": 25000,
                    "current_debt": 3000,
                    "monthly_payment": 1500,
                }
            ],
        }
    }

    state["needs_analysis"] = {
        "product_category": "tv",
        "must_have_features": ["55 inç", "akıllı TV"],
        "budget_max": 40000,
        "budget_currency": "TRY",
        "use_case": "family_movie_watching",
        "confidence": 0.95,
    }

    state["research_intel"] = {
        "consensus_summary": "55 inç akıllı TV pazarında LG, Philips, Samsung, TCL lider markalar",
        "top_evaluations": [
            {
                "name": "Philips 55PUS8500",
                "brand": "Philips",
                "estimated_price_try": 34199,
                "is_within_budget": True,
                "overall_score": 7.6,
                "turkey_perspective": "Türkiye'de iyi servis ağı",
                "strengths": ["Ambilight", "4K HDR", "Smart TV özellikleri"],
                "cautions": ["TV hoparlörü orta"],
            },
            {
                "name": "LG OLED55C54LA",
                "brand": "LG",
                "estimated_price_try": 38000,
                "is_within_budget": True,
                "overall_score": 8.5,
                "strengths": ["OLED ekran", "Mükemmel siyah seviyesi"],
                "cautions": ["Daha pahalı"],
            },
        ],
    }

    state["market_intel"] = {
        "products": [
            {
                "product_name": "Philips 55PUS8500",
                "brand": "Philips",
                "best_price": 34199,
                "best_seller": {
                    "seller_name": "Cimri (Çeşitli satıcılar)",
                    "rating": 4.5,
                    "installment_info": "12 ay vade farksız",
                },
            }
        ],
    }

    state["finance_analysis"] = {
        "profile_complete": True,
        "cash_flow": {
            "monthly_income": 35000,
            "monthly_total_expenses": 18500,
            "disposable_income": 16500,
            "debt_to_income_ratio": 0.04,
            "healthy_purchase_capacity": 5000,
        },
        "purchase_feasibility": {
            "feasibility": "rahat",
            "recommendation": "installment_6",
            "reasoning": "6 ay vade farksız taksit cash flow'a uygun",
        },
        "coaching_message": "Bu alımı rahatlıkla yapabilirsiniz",
        "warnings": [
            "Acil durum fonunuz hedeften az (50K vs 55.5K önerilen)",
            "Peşin alım acil fonu kritik seviyeye düşürür",
            "Kredi kartı borcu (3K) faiz işliyor, öncelikli kapatın",
        ],
        "confidence": 0.95,
    }

    state["tco_analysis"] = {
        "product_name": "Philips 55PUS8500",
        "breakdown": {
            "purchase_price": 34199,
            "energy_label": "E",
            "annual_kwh_min": 260,
            "annual_kwh_max": 330,
            "annual_kwh_avg": 295,
            "kwh_price_try": 3.24,
            "electricity_5yr_min": 4212,
            "electricity_5yr_max": 5346,
            "electricity_5yr_avg": 4779,
        },
        "service_reliability": {
            "level": "low",
            "summary": "Philips 55PUS8500 model televizyon için şikayet sıklığı düşüktür. Ürün 2025 yılında piyasaya sürülmüş olup, doğrudan bu modele yönelik çok az şikayet bulunmaktadır.",
            "common_issues": [
                "YouTube uygulamasının açılmaması (Kasım 2025)",
                "Wi-Fi bağlantı sorunları (Ağustos 2025 - Şubat 2026)",
            ],
            "active_complaints_last_12m": True,
            "complaint_time_range": "2025-2026",
        },
        "accessories_recommended": [
            {
                "name": "Soundbar",
                "price_range": "3.000-15.000 TL",
                "why_needed": "TV'lerin dahili hoparlörleri yetersiz, soundbar ile film deneyimi iyileşir",
                "importance": "recommended",
            },
            {
                "name": "HDMI Kablo (4K)",
                "price_range": "100-500 TL",
                "why_needed": "Oyun konsolu/bilgisayar bağlamak için",
                "importance": "essential",
            },
            {
                "name": "Duvar Montaj Kiti",
                "price_range": "300-1.500 TL",
                "why_needed": "Estetik kullanım, yer tasarrufu",
                "importance": "optional",
            },
            {
                "name": "Akım Korumalı Priz",
                "price_range": "200-800 TL",
                "why_needed": "Elektrik dalgalanmalarından koruma",
                "importance": "recommended",
            },
        ],
        "data_sources": {
            "energy_label_source": "grounding",
            "kwh_price_source": "grounding",
            "accessories_source": "grounding",
            "service_reliability_source": "grounding",
        },
        "coaching_message": "Philips 55PUS8500 elektrik maliyeti detayları...",
        "confidence": 0.85,
    }

    start = time.time()
    agent = StrategyAgent()
    result = await agent.run(state)
    elapsed = time.time() - start

    print(f"\n⏱️  Süre: {elapsed:.1f} saniye")

    strategy = result.get("final_strategy")
    if not strategy:
        print("❌ HATA: final_strategy boş")
        for err in result.get("errors", []):
            print(f"   - {err}")
        return

    print(f"\n🎭 PERSONA: {strategy['persona_detected']}")
    print(f"   Sebep: {strategy['persona_reasoning']}")

    rec = strategy["recommended_product"]
    print(f"\n🏆 ANA ÖNERİ:")
    print(f"   {rec['name']} - {rec['price_try']:,.0f} TL @ {rec['best_seller']}")
    print(f"   Neden: {rec['why_chosen'][:300]}")
    print(f"   Güçlü yönler:")
    for s in rec.get('strengths', [])[:5]:
        print(f"      ✅ {s}")
    print(f"   Bilinmesi gerekenler:")
    for c in rec.get('considerations', [])[:5]:
        print(f"      ⚠️ {c}")

    alts = strategy.get("alternatives", [])
    print(f"\n🥈 ALTERNATİFLER ({len(alts)}):")
    for a in alts:
        print(f"   • {a['name']} ({a['tier']}, {a['price_try']:,.0f} TL)")
        print(f"     {a['one_line_reason']}")
        print(f"     Trade-off: {a['trade_off']}")

    actions = strategy.get("action_plan", [])
    print(f"\n📋 EYLEM PLANI ({len(actions)} adım):")
    for a in actions:
        priority_emoji = {"critical": "🚨", "important": "⚠️", "normal": "💡"}.get(a['priority'], "•")
        print(f"   {priority_emoji} {a['order']}. {a['action']}")
        print(f"      Sebep: {a['why']}")

    warnings = strategy.get("warnings", [])
    print(f"\n⚠️  UYARILAR ({len(warnings)}):")
    for w in warnings:
        print(f"   • {w}")

    print(f"\n💬 FINAL MESAJ:")
    print(strategy.get("final_message", "")[:2000])
    print("...")

    print(f"\n📊 Confidence: {strategy.get('confidence', 0):.2f}")


async def main():
    await test_with_full_data()

    print(f"\n{'=' * 80}")
    print("✅ Test tamamlandı")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(main())