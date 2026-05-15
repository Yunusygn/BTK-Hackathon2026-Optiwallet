"""
ResearchAgent v2 Test Script — Multi-Criteria Decision Analysis.

Test scenario: 55 inç TV, 25K bütçe, ailecek film izleme.
"""

from __future__ import annotations

import asyncio
import json

from app.agents.research import ResearchAgent
from app.agents.workflow import create_initial_state


async def test_research_v2():
    """Multi-criteria research test."""
    print("=" * 80)
    print("🔬 RESEARCH AGENT v2 TEST — Multi-Criteria Decision Analysis")
    print("=" * 80)
    print()

    # Test state — NeedsAnalysis çıktısını simüle et
    import uuid
    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query="55 inç akıllı TV, 25K bütçe, ailecek film izleyeceğiz",
    )

    state["needs_analysis"] = {
        "product_category": "tv",
        "product_subcategory": "smart_tv",
        "must_have_features": ["55_inch", "smart_tv"],
        "nice_to_have_features": ["4k", "hdr"],
        "budget_min": None,
        "budget_max": 25000,
        "budget_currency": "TRY",
        "use_case": "family_movie_watching",
        "confidence": 0.95,
    }

    # Agent'ı çalıştır
    agent = ResearchAgent()
    result_state = await agent.run(state)

    research = result_state.get("research_intel")

    if not research:
        print("❌ HATA: research_intel boş!")
        print("Hata mesajları:")
        for err in result_state.get("errors", []):
            print(f"   - {err}")
        return

    # ===== Çıktıları Yazdır =====
    print("\n📋 CONSENSUS SUMMARY:")
    print("-" * 80)
    print(research["consensus_summary"])

    evaluations = research.get("evaluations", [])
    print(f"\n📊 {len(evaluations)} MARKA/MODEL DEĞERLENDİRMESİ:")
    print("=" * 80)

    for i, ev in enumerate(evaluations, 1):
        print(f"\n{i}. {ev['name']} ({ev.get('brand', 'N/A')})")
        print("-" * 80)

        # 6 boyut skorları
        dimensions = [
            ("Performans", ev["performance"]),
            ("Güvenilirlik", ev["reliability"]),
            ("Servis & Destek", ev["service_support"]),
            ("Fiyat/Performans", ev["value_for_money"]),
            ("Kullanıcı Memnuniyeti", ev["user_satisfaction"]),
            ("Uzun Vadeli Kalite", ev["long_term_quality"]),
        ]

        for dim_name, dim_data in dimensions:
            score = dim_data["score"]
            conf = dim_data["confidence"]
            sources = dim_data["source_count"]
            bar = "█" * int(score) + "░" * (10 - int(score))
            print(
                f"   {dim_name:25s} {bar} {score:4.1f}/10  "
                f"(güven: {conf:.2f}, {sources} kaynak)"
            )

        print(f"\n   📌 Genel Skor: {ev['overall_score']:.2f}/10")

        print(f"\n   🇹🇷 Türkiye: {ev['turkey_perspective'][:200]}...")
        print(f"   🌍 Global:  {ev['global_perspective'][:200]}...")

        print("\n   ✅ Güçlü Yönler:")
        for s in ev["strengths"][:3]:
            print(f"      • {s}")

        print("\n   ⚠️ Dikkat:")
        for c in ev["cautions"][:3]:
            print(f"      • {c}")

    # Forum quotes
    quotes = research.get("forum_quotes", [])
    if quotes:
        print(f"\n💬 FORUM ALINTILARI ({len(quotes)}):")
        for q in quotes[:5]:
            sentiment = q.get("sentiment", "neutral")
            emoji = "👍" if sentiment == "positive" else "👎" if sentiment == "negative" else "💭"
            print(f"   {emoji} [{q.get('source', '?')}]: \"{q.get('quote', '')[:150]}...\"")

    # Category insights
    insights = research.get("category_insights", [])
    if insights:
        print(f"\n💡 KATEGORİ İÇGÖRÜLERİ ({len(insights)}):")
        for ins in insights:
            print(f"   • {ins}")

    # Sources
    sources = research.get("sources", [])
    print(f"\n📚 KAYNAKLAR ({len(sources)}):")
    for s in sources[:10]:
        print(f"   → [{s['source_type']}] {s['title'][:60]}")

    print("\n" + "=" * 80)
    print(f"✅ TEST BAŞARILI! (confidence: {research['confidence']})")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_research_v2())