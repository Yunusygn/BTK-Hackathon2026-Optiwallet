"""MarketAgent test - Pazar dedektifi."""

from __future__ import annotations

import asyncio
import uuid

from app.agents.market import MarketAgent
from app.agents.workflow import create_initial_state


async def main():
    print("=" * 80)
    print("💰 MARKET AGENT TEST — Piyasa Dedektifi")
    print("=" * 80)

    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query="55 inç TV, 25K bütçe",
    )

    # needs_analysis manuel
    state["needs_analysis"] = {
        "product_category": "tv",
        "product_subcategory": None,
        "must_have_features": ["55_inch", "smart_tv"],
        "nice_to_have_features": [],
        "budget_min": None,
        "budget_max": 40000,
        "budget_currency": "TRY",
        "use_case": "family_movie_watching",
        "confidence": 0.95,
    }

    # research_intel mock (top 4 marka)
    state["research_intel"] = {
        "top_evaluations": [
            {
                "name": "TCL 55Q6C",
                "brand": "TCL",
                "estimated_price_try": 22000,
                "overall_score": 7.5,
            },
            {
                "name": "Samsung 55CU8000",
                "brand": "Samsung",
                "estimated_price_try": 23500,
                "overall_score": 7.4,
            },
            {
                "name": "Xiaomi TV A Pro 55",
                "brand": "Xiaomi",
                "estimated_price_try": 19500,
                "overall_score": 7.3,
            },
        ],
        "alternative_evaluations": [],
        "market_overview": [],
    }

    agent = MarketAgent()
    result_state = await agent.run(state)

    market = result_state.get("market_intel")

    if not market:
        print("\n❌ HATA: market_intel boş!")
        for err in result_state.get("errors", []):
            print(f"   - {err}")
        return

    print(f"\n📋 PAZAR ÖZETİ:")
    print(f"   {market['market_summary']}")

    print(f"\n📊 BÜTÇE DURUMU:")
    bs = market.get("budget_status", {})
    print(f"   Kullanıcı bütçesi: {bs.get('user_budget', 'N/A')} TL")
    print(f"   Bütçeye giren: {bs.get('in_budget_count', 0)}")
    print(f"   Bütçe üstü: {bs.get('out_of_budget_count', 0)}")

    products = market.get("products", [])
    print(f"\n🛒 ÜRÜNLER ({len(products)}):")

    for i, p in enumerate(products, 1):
        print(f"\n   {i}. {p['product_name']}")
        print(f"      💰 En iyi fiyat: {p['best_price']} TL")
        best = p.get("best_seller", {})
        print(f"      🏪 En iyi satıcı: {best.get('seller_name')}")
        print(f"         Puan: {best.get('rating', 'N/A')}/5")
        print(f"         Teslimat: {best.get('delivery_info', 'N/A')}")
        print(f"         Taksit: {best.get('installment_info', 'N/A')}")

        all_sellers = p.get("all_sellers", [])
        if len(all_sellers) > 1:
            print(f"      📋 Diğer satıcılar ({len(all_sellers) - 1}):")
            for s in all_sellers[1:4]:
                price = s.get('price_try')
                price_str = f"{price} TL" if price else "Fiyat bilinmiyor"
                print(f"         • {s['seller_name']}: {price_str}")

        history = p.get("price_history")
        if history:
            trend = history.get('trend', 'N/A')
            change = history.get('percent_change')
            if change is not None:
                print(f"      📈 Fiyat trendi: {trend} ({change:+.1f}%)")
            else:
                print(f"      📈 Fiyat trendi: {trend}")

        campaign = p.get("campaign_alert")
        if campaign:
            print(f"      🎉 Kampanya: {campaign}")

    sources = market.get("sources", [])
    print(f"\n📚 KAYNAKLAR ({len(sources)}):")
    for s in sources[:5]:
        print(f"   → [{s.get('source_type', '')}] {s.get('title', '')[:80]}")

    print("\n" + "=" * 80)
    print(f"✅ TEST BAŞARILI! (confidence: {market['confidence']:.2f})")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())