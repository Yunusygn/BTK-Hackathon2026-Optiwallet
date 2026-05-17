"""
Full Pipeline Test — End-to-End.

Test scenarios:
1. NET query + financial profile → Full pipeline (4 agents)
2. NET query without profile → Generic finance coaching
3. Ambiguous query → ConsultantAgent clarification (skip pipeline)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid

from app.agents.workflow import create_initial_state, get_workflow


async def test_scenario(
    name: str,
    user_query: str,
    financial_profile: dict | None = None,
):
    """Tek senaryo end-to-end test."""
    print(f"\n{'=' * 80}")
    print(f"🎯 SENARYO: {name}")
    print(f"   Kullanıcı: \"{user_query}\"")
    if financial_profile:
        income = financial_profile.get("monthly_income", 0)
        print(f"   Finansal profil: {income:,} TL/ay gelir")
    else:
        print(f"   Finansal profil: YOK")
    print('=' * 80)

    workflow = get_workflow()
    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query=user_query,
        user_context={
            "financial_profile": financial_profile,
        } if financial_profile else {},
    )

    start = time.time()
    result = await workflow.ainvoke(state)
    elapsed = time.time() - start

    print(f"\n⏱️  TOPLAM SÜRE: {elapsed:.1f} saniye")

    # === Consultant ===
    consultant = result.get("consultant_output")
    if consultant:
        print(f"\n📍 STEP 1 — CONSULTANT:")
        print(f"   Mode: {consultant['interaction_mode']}")
        print(f"   Ready: {consultant['ready_for_pipeline']}")
        print(f"   Confidence: {consultant['confidence']:.2f}")

        if consultant.get("clarification_questions"):
            print(f"   ⏸️  Pipeline durdu (clarification gerekli)")
            print(f"   Sorular ({len(consultant['clarification_questions'])}):")
            for q in consultant['clarification_questions'][:3]:
                print(f"      • {q['question']}")
            return

    # === Research ===
    research = result.get("research_intel")
    if research:
        top = research.get("top_evaluations", [])
        print(f"\n📍 STEP 2 — RESEARCH:")
        print(f"   Toplam taranan: {research.get('total_brands_scanned', 0)}")
        print(f"   Bütçeye giren: {research.get('brands_in_budget', 0)}")
        print(f"   Top {len(top)} marka:")
        for t in top[:4]:
            score = t.get('overall_score', 'N/A')
            score_str = f"{score:.1f}" if isinstance(score, (int, float)) else str(score)
            print(f"      • {t['name']} (skor: {score_str})")

    # === Market ===
    market = result.get("market_intel")
    if market:
        products = market.get("products", [])
        bs = market.get("budget_status", {})
        print(f"\n📍 STEP 3 — MARKET:")
        print(f"   Bütçeye giren: {bs.get('in_budget_count', 0)}")
        print(f"   Bütçe üstü: {bs.get('out_of_budget_count', 0)}")
        if products:
            print(f"   En iyi seçenekler ({len(products)}):")
            for p in products[:3]:
                seller = p.get("best_seller", {})
                print(f"      • {p['product_name']}")
                print(f"        💰 {p['best_price']:,.0f} TL @ {seller.get('seller_name', 'N/A')}")

    # === Finance ===
    finance = result.get("finance_analysis")
    if finance:
        print(f"\n📍 STEP 4 — FINANCE:")
        print(f"   Profile complete: {finance['profile_complete']}")
        print(f"   Confidence: {finance['confidence']:.2f}")

        cf = finance.get("cash_flow")
        if cf:
            print(f"   💰 Disposable income: {cf.get('disposable_income', 0):,.0f} TL")
            print(f"   📊 Borç/Gelir oranı: {cf.get('debt_to_income_ratio', 0):.2f}")

        pf = finance.get("purchase_feasibility")
        if pf:
            print(f"   🎯 Fizibilite: {pf['feasibility'].upper()}")
            print(f"   ✅ Tavsiye: {pf['recommendation']}")

        warnings = finance.get("warnings", [])
        if warnings:
            print(f"   ⚠️  Uyarılar ({len(warnings)}):")
            for w in warnings[:3]:
                print(f"      • {w}")

        msg = finance.get("coaching_message", "")
        if msg:
            print(f"\n   💬 KOÇLUK MESAJI ÖZETİ:")
            print(f"      {msg[:300]}...")

    # STEP 5 — TCO
        tco = result.get("tco_analysis")
        if tco:
            print(f"\n📍 STEP 5 — TCO (Elektrik Maliyeti):")
            bd = tco.get("breakdown", {})

            print(f"   ⚡ Enerji etiketi: {bd.get('energy_label', 'N/A')}")
            print(f"   🔋 Yıllık tüketim: {bd.get('annual_kwh_min', 0):.0f}-"
                  f"{bd.get('annual_kwh_max', 0):.0f} kWh")
            print(f"   💡 kWh fiyatı: {bd.get('kwh_price_try', 0):.2f} TL")
            print(f"   💸 5-yıl elektrik: {bd.get('electricity_5yr_min', 0):,.0f}-"
                  f"{bd.get('electricity_5yr_max', 0):,.0f} TL")

            # Servis
            service = tco.get("service_reliability")
            if service:
                level = service.get('level', 'N/A')
                level_emoji = {
                    "low": "✅",
                    "medium": "🟡",
                    "high": "⚠️",
                }.get(level, "❓")
                print(f"\n   🔧 Servis: {level_emoji} {level.upper()}")
                if service.get('complaint_time_range'):
                    print(f"   📅 Şikayet dönemi: {service['complaint_time_range']}")
                active_12m = service.get('active_complaints_last_12m')
                if active_12m is True:
                    print(f"   ⚠️  Son 12 ay AKTİF şikayet")
                elif active_12m is False:
                    print(f"   ✅ Son 12 ay aktif ciddi şikayet YOK")

                issues = service.get('common_issues', [])
                if issues:
                    print(f"   Yaygın sorunlar:")
                    for issue in issues[:3]:
                        print(f"      • {issue[:150]}")

            # Aksesuar
            accessories = tco.get("accessories_recommended", [])
            if accessories:
                print(f"\n   🎁 Aksesuar önerileri ({len(accessories)}):")
                for a in accessories[:3]:
                    importance_emoji = {
                        "essential": "⭐",
                        "recommended": "✅",
                        "optional": "💡",
                    }.get(a.get('importance', 'optional'), "💡")
                    print(f"      {importance_emoji} {a.get('name', 'N/A')} "
                          f"({a.get('price_range', 'N/A')})")        

    # STEP 6 — STRATEGY (Final Sentez)
        strategy = result.get("final_strategy")
        if strategy:
            print(f"\n📍 STEP 6 — STRATEGY (Final Sentez):")
            print(f"   🎭 Persona: {strategy.get('persona_detected', 'N/A')}")

            rec = strategy.get("recommended_product", {})
            print(f"\n   🏆 ANA ÖNERİ:")
            print(f"      {rec.get('name', 'N/A')} - "
                  f"{rec.get('price_try', 0):,.0f} TL")
            print(f"      Neden: {rec.get('why_chosen', '')[:300]}")

            alts = strategy.get("alternatives", [])
            if alts:
                print(f"\n   🥈 ALTERNATİFLER ({len(alts)}):")
                for a in alts[:2]:
                    print(f"      • {a.get('name', 'N/A')} "
                          f"({a.get('tier', '')}, "
                          f"{a.get('price_try', 0):,.0f} TL)")

            actions = strategy.get("action_plan", [])
            if actions:
                print(f"\n   📋 EYLEM PLANI ({len(actions)} adım):")
                for a in actions[:5]:
                    priority_emoji = {
                        "critical": "🚨",
                        "important": "⚠️",
                        "normal": "💡",
                    }.get(a.get('priority', 'normal'), "•")
                    print(f"      {priority_emoji} {a.get('order', '?')}. "
                          f"{a.get('action', '')[:150]}")

            warnings = strategy.get("warnings", [])
            if warnings:
                print(f"\n   ⚠️  UYARILAR ({len(warnings)}):")
                for w in warnings[:3]:
                    print(f"      • {w[:200]}")

            print(f"\n   💬 FINAL MESAJ:")
            print(f"   {strategy.get('final_message', '')[:600]}...")        

    # === Errors ===
    errors = result.get("errors", [])
    if errors:
        print(f"\n❌ HATALAR ({len(errors)}):")
        for err in errors[:3]:
            print(f"   - {err.get('agent')}: {err.get('error', '')[:150]}")

    print(f"\n✅ SENARYO TAMAMLANDI")


async def main():
    print("=" * 80)
    print("🚀 FULL PIPELINE TEST — End-to-End (6 Agent)")
    print("=" * 80)

    # SENARYO 1: Full pipeline (Net query + financial profile)
    await test_scenario(
        "FULL PIPELINE — Net query + Rahat profil",
        "55 inç akıllı TV, 40K bütçe, ailecek film izleyeceğiz",
        financial_profile={
            "monthly_income": 35000,
            "monthly_fixed_expenses": 12000,
            "monthly_variable_expenses": 5000,
            "current_savings": 50000,
            "consumer_loans_monthly": 1500,
            "credit_cards": [
                {
                    "bank_name": "Garanti BBVA",
                    "card_name": "Bonus",
                    "credit_limit": 25000,
                    "current_debt": 3000,
                    "monthly_payment": 500,
                },
            ],
        },
    )

    await asyncio.sleep(3)

    # SENARYO 2: Full pipeline (Net query but NO profile)
    await test_scenario(
        "FULL PIPELINE — Net query, profile YOK",
        "55 inç akıllı TV, 40K bütçe, ailecek film izleyeceğiz",
        financial_profile=None,
    )

    await asyncio.sleep(3)

    # SENARYO 3: Clarification (pipeline başlamaz)
    await test_scenario(
        "CLARIFICATION — Ambiguous query",
        "TV almak istiyorum",
        financial_profile=None,
    )

    print(f"\n{'=' * 80}")
    print("✅ Full Pipeline Test Tamamlandı!")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(main())