"""Workflow test - ConsultantAgent + ResearchAgent entegrasyonu."""

from __future__ import annotations

import asyncio
import json
import uuid

from app.agents.workflow import create_initial_state, get_workflow


async def test_scenario(name: str, user_query: str):
    """Tek senaryo test."""
    print(f"\n{'=' * 80}")
    print(f"🧪 SENARYO: {name}")
    print(f"   Kullanıcı: \"{user_query}\"")
    print('=' * 80)

    workflow = get_workflow()
    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query=user_query,
    )

    # Workflow'u çalıştır
    result = await workflow.ainvoke(state)

    # Consultant output
    consultant = result.get("consultant_output")
    if consultant:
        print(f"\n📊 CONSULTANT MOD: {consultant['interaction_mode']}")
        print(f"📊 READY: {consultant['ready_for_pipeline']}")
        print(f"📊 CONFIDENCE: {consultant['confidence']:.2f}")

        if consultant.get("clarification_questions"):
            print(f"\n❓ SORULAR ({len(consultant['clarification_questions'])}):")
            for q in consultant['clarification_questions']:
                print(f"   {q['question']}")

    # Research output
    research = result.get("research_intel")
    if research:
        print(f"\n🔬 RESEARCH ÇALIŞTI:")
        evaluations = research.get("evaluations", [])
        print(f"   Marka sayısı: {len(evaluations)}")
        for e in evaluations[:3]:
            print(f"   • {e['name']} — Skor: {e.get('overall_score', 'N/A')}")
    else:
        print(f"\n⏸️  Research çalışmadı (clarification döngüsünde)")

    # Errors
    errors = result.get("errors", [])
    if errors:
        print(f"\n❌ HATALAR ({len(errors)}):")
        for err in errors[:3]:
            print(f"   - {err.get('error', err)[:200]}")


async def main():
    scenarios = [
        ("NET → Pipeline çalışmalı",
         "55 inç akıllı TV, 25K bütçe, ailecek film izleyeceğiz"),

        ("YARI NET → Soru sormalı",
         "55 inç TV almak istiyorum"),

        ("KARARSIZ → 3 soru sormalı",
         "TV almak istiyorum"),
    ]

    for name, query in scenarios:
        try:
            await test_scenario(name, query)
        except Exception as exc:
            print(f"\n❌ Senaryo hatası: {exc}")

        await asyncio.sleep(2)

    print(f"\n{'=' * 80}")
    print("✅ Workflow test tamamlandı!")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(main())