"""ResearchAgent v3 test - Hibrit Smart Filter + Tournament."""

from __future__ import annotations

import asyncio
import uuid

from app.agents.research_v3 import ResearchAgentV3
from app.agents.workflow import create_initial_state


async def main():
    print("=" * 80)
    print("🔬 RESEARCH AGENT v3 TEST — Hibrit Smart Filter + Tournament")
    print("=" * 80)

    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query="55 inç TV, 25K bütçe, ailecek film",
    )

    # needs_analysis manuel
    state["needs_analysis"] = {
        "product_category": "tv",
        "product_subcategory": None,
        "must_have_features": ["55_inch", "smart_tv"],
        "nice_to_have_features": [],
        "budget_min": None,
        "budget_max": 25000,
        "budget_currency": "TRY",
        "use_case": "family_movie_watching",
        "confidence": 0.95,
    }

    agent = ResearchAgentV3()
    result_state = await agent.run(state)

    research = result_state.get("research_intel")

    if not research:
        print("\n❌ HATA: research_intel boş!")
        for err in result_state.get("errors", []):
            print(f"   - {err}")
        return

    print(f"\n📋 ÖZET:")
    print(f"   {research['consensus_summary'][:300]}...")

    print(f"\n📊 İSTATİSTİKLER:")
    print(f"   Toplam taranan: {research['total_brands_scanned']}")
    print(f"   Bütçeye giren: {research['brands_in_budget']}")
    print(f"   Confidence: {research['confidence']:.2f}")

    # TIER 1
    top = research.get("top_evaluations", [])
    print(f"\n🥇 TOP 4 ({len(top)} marka):")
    for i, t in enumerate(top, 1):
        print(f"\n   {i}. {t['name']}")
        print(f"      Skor: {t.get('overall_score', 'N/A')}")
        print(f"      Bütçe içi: {t.get('is_within_budget', 'N/A')}")

    # TIER 2
    alts = research.get("alternative_evaluations", [])
    print(f"\n🥈 ALTERNATİFLER ({len(alts)} marka):")
    for a in alts:
        print(f"   • {a['name']} (skor: {a.get('overall_score', 'N/A')})")
        print(f"     {a.get('one_line_summary', '')}")
        print(f"     Neden top değil: {a.get('why_not_top', '')}")

    # TIER 3
    market = research.get("market_overview", [])
    print(f"\n🥉 PAZAR ÖZETİ ({len(market)} marka):")
    for m in market:
        print(f"   • {m['name']} [{m.get('status', '')}] — {m.get('note', '')}")

    # Kaynaklar
    sources = research.get("sources", [])
    print(f"\n📚 KAYNAKLAR ({len(sources)}):")
    for s in sources[:5]:
        print(f"   → [{s.get('source_type', '')}] {s.get('title', '')[:80]}")

    print("\n" + "=" * 80)
    print(f"✅ TEST BAŞARILI! (confidence: {research['confidence']:.2f})")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())