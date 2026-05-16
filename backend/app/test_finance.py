"""FinanceAgent test - 3 senaryo."""

from __future__ import annotations

import asyncio
import uuid

from app.agents.finance import FinanceAgent
from app.agents.workflow import create_initial_state


async def test_scenario(name: str, financial_profile: dict | None):
    """Tek senaryo test."""
    print(f"\n{'=' * 80}")
    print(f"🧪 SENARYO: {name}")
    print('=' * 80)

    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query="55 inç TV, 40K bütçe",
        user_context={
            "financial_profile": financial_profile,
        } if financial_profile else {},
    )

    # Mock dependencies
    state["needs_analysis"] = {
        "product_category": "tv",
        "budget_max": 40000,
        "use_case": "family_movie_watching",
    }

    state["market_intel"] = {
        "products": [
            {
                "product_name": "Samsung 55CU8000",
                "brand": "Samsung",
                "best_price": 23999,
                "is_within_budget": True,
            }
        ],
        "market_summary": "Pazar analizi tamam",
        "budget_status": {"user_budget": 40000, "in_budget_count": 1},
    }

    agent = FinanceAgent()
    result_state = await agent.run(state)

    finance = result_state.get("finance_analysis")

    if not finance:
        print("\n❌ HATA: finance_analysis boş!")
        for err in result_state.get("errors", []):
            print(f"   - {err.get('error', err)[:300]}")
        return

    print(f"\n📊 PROFILE COMPLETE: {finance['profile_complete']}")
    print(f"📊 CONFIDENCE: {finance['confidence']:.2f}")

    # Cash Flow
    cf = finance.get("cash_flow")
    if cf:
        print(f"\n💰 CASH FLOW:")
        print(f"   Aylık gelir: {cf.get('monthly_income', 0):,.0f} TL")
        print(f"   Toplam gider: {cf.get('monthly_total_expenses', 0):,.0f} TL")
        print(f"   Disposable: {cf.get('disposable_income', 0):,.0f} TL")
        print(f"   Mevcut borç (aylık): {cf.get('current_debt_monthly', 0):,.0f} TL")
        print(f"   Borç/Gelir oranı: {cf.get('debt_to_income_ratio', 0):.2f}")
        print(f"   Sağlıklı alım kapasitesi: {cf.get('healthy_purchase_capacity', 0):,.0f} TL/ay")

    # Feasibility
    pf = finance.get("purchase_feasibility")
    if pf:
        print(f"\n🎯 FIZIBILITE: {pf['feasibility'].upper()}")
        print(f"   Tavsiye: {pf['recommendation']}")
        print(f"   Sebep: {pf['reasoning'][:300]}...")

        installments = pf.get("installment_options", [])
        if installments:
            print(f"\n💳 TAKSIT SEÇENEKLERİ:")
            for inst in installments[:4]:
                print(f"   • {inst['months']} ay: {inst['monthly_payment']:,.0f} TL/ay "
                      f"(toplam {inst['total_cost']:,.0f} TL, "
                      f"vade farkı: {inst.get('vade_farki', 0)} TL) "
                      f"- {inst.get('recommendation_level', 'N/A')}")

    # Coaching
    print(f"\n💬 KOÇLUK MESAJI:")
    print(f"   {finance['coaching_message'][:600]}...")

    # Warnings
    warnings = finance.get("warnings", [])
    if warnings:
        print(f"\n⚠️  UYARILAR ({len(warnings)}):")
        for w in warnings:
            print(f"   • {w}")


async def main():
    print("=" * 80)
    print("🏦 FINANCE AGENT TEST — Cash Flow + Borç Analizi")
    print("=" * 80)

    # SENARYO 1: Tam profil — Rahat durum
    await test_scenario(
        "TAM PROFİL — Rahat durum (yüksek gelir, az borç)",
        {
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
            "upcoming_expenses": ["Vergi (Mayıs)", "Sigorta (Haziran)"],
        },
    )

    await asyncio.sleep(2)

    # SENARYO 2: Sıkışık durum
    await test_scenario(
        "SIKIŞIK DURUM (orta gelir, yüksek borç)",
        {
            "monthly_income": 22000,
            "monthly_fixed_expenses": 11000,
            "monthly_variable_expenses": 6000,
            "current_savings": 5000,
            "consumer_loans_monthly": 3000,
            "credit_cards": [
                {
                    "bank_name": "Akbank",
                    "card_name": "Wings",
                    "credit_limit": 15000,
                    "current_debt": 8000,
                    "monthly_payment": 1500,
                },
                {
                    "bank_name": "Yapı Kredi",
                    "card_name": "WorldCard",
                    "credit_limit": 10000,
                    "current_debt": 4500,
                    "monthly_payment": 1000,
                },
            ],
        },
    )

    await asyncio.sleep(2)

    # SENARYO 3: Profile yok
    await test_scenario(
        "PROFİL YOK (kullanıcı bilgi paylaşmadı)",
        None,
    )

    print(f"\n{'=' * 80}")
    print("✅ Tüm testler tamamlandı!")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(main())