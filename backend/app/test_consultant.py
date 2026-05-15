"""ConsultantAgent test script."""

from __future__ import annotations

import asyncio
import json
import uuid

from app.agents.consultant import ConsultantAgent
from app.agents.workflow import create_initial_state


async def test_scenario(name: str, user_query: str):
    """Tek senaryo test."""
    print(f"\n{'=' * 80}")
    print(f"🧪 SENARYO: {name}")
    print(f"   Kullanıcı: \"{user_query}\"")
    print('=' * 80)

    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query=user_query,
    )

    agent = ConsultantAgent()
    result_state = await agent.run(state)

    output = result_state.get("consultant_output")

    if not output:
        print("❌ HATA: consultant_output boş!")
        for err in result_state.get("errors", []):
            print(f"   - {err}")
        return

    print(f"\n📊 MOD: {output['interaction_mode']}")
    print(f"📊 READY: {output['ready_for_pipeline']}")
    print(f"📊 CONFIDENCE: {output['confidence']:.2f}")
    print(f"\n💬 MESAJ:\n{output['message_to_user']}")

    if output.get("parsed_needs"):
        print(f"\n✅ ÇIKARILAN İHTİYAÇLAR:")
        print(json.dumps(output['parsed_needs'], indent=2, ensure_ascii=False))

    if output.get("clarification_questions"):
        print(f"\n❓ SORULAR ({len(output['clarification_questions'])}):")
        for q in output['clarification_questions']:
            print(f"\n   {q['question']}")
            for o in q['options']:
                print(f"      □ {o['label']}")

    if output.get("educational_content"):
        print(f"\n📚 EĞİTİM İÇERİĞİ:")
        print(output['educational_content'])


async def main():
    """Tüm senaryoları çalıştır."""
    scenarios = [
        ("NET İSTEK", "55 inç akıllı TV, 25K bütçe, ailecek film izleyeceğiz"),
        ("YARI NET", "55 inç TV almak istiyorum"),
        ("KARARSIZ", "TV almak istiyorum"),
        ("KATEGORİ BELİRSİZ", "Bir şey almak istiyorum"),
        ("EĞİTİM MODU", "TV alırken nelere bakmalıyım"),
        ("LAPTOP NET", "40K bütçeyle gaming için laptop arıyorum"),
        ("LAPTOP BELİRSİZ", "Laptop almak istiyorum"),
    ]

    for name, query in scenarios:
        try:
            await test_scenario(name, query)
        except Exception as exc:
            print(f"\n❌ Hata: {exc}")

        # Rate limit için kısa bekleme
        await asyncio.sleep(2)

    print(f"\n{'=' * 80}")
    print("✅ Tüm testler tamamlandı!")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(main())