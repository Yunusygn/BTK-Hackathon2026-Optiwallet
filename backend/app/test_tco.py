"""TCOAgent v3 test — Lean Honesty + Grounding (Aksesuar + Servis)."""

from __future__ import annotations

import asyncio
import time
import uuid

from app.agents.tco import TCOAgent
from app.agents.workflow import create_initial_state


async def test_scenario(name: str, category: str, product_name: str, price: float):
    """Tek senaryo test."""
    print(f"\n{'=' * 80}")
    print(f"🧪 SENARYO: {name}")
    print(f"   Kategori: {category}")
    print(f"   Ürün: {product_name}")
    print(f"   Fiyat: {price:,.0f} TL")
    print('=' * 80)

    state = create_initial_state(
        session_id=str(uuid.uuid4()),
        user_query=f"{category} test",
    )

    state["needs_analysis"] = {
        "product_category": category,
        "budget_max": price * 1.2,
    }

    state["market_intel"] = {
        "products": [
            {
                "product_name": product_name,
                "best_price": price,
            }
        ],
    }

    start = time.time()
    agent = TCOAgent()
    result = await agent.run(state)
    elapsed = time.time() - start

    print(f"\n⏱️  Süre: {elapsed:.1f} saniye")

    tco = result.get("tco_analysis")
    if not tco:
        print("❌ HATA: tco_analysis boş")
        for err in result.get("errors", []):
            print(f"   - {err}")
        return

    bd = tco["breakdown"]
    ds = tco["data_sources"]

    print(f"\n📊 DATA SOURCES:")
    print(f"   Enerji etiketi: {ds['energy_label_source']}")
    print(f"   kWh fiyatı: {ds['kwh_price_source']}")
    print(f"   Aksesuar: {ds.get('accessories_source', 'N/A')}")
    print(f"   Servis: {ds.get('service_reliability_source', 'N/A')}")

    print(f"\n⚡ ENERJİ:")
    print(f"   Etiket: {bd['energy_label']}")
    print(f"   Yıllık tüketim: {bd['annual_kwh_min']:.0f} - {bd['annual_kwh_max']:.0f} kWh "
          f"(ortalama: {bd['annual_kwh_avg']:.0f})")
    print(f"   kWh fiyatı: {bd['kwh_price_try']:.2f} TL")

    print(f"\n💰 BREAKDOWN:")
    print(f"   Alış: {bd['purchase_price']:,.0f} TL (GERÇEK)")

    # Yıllık elektrik (5'e böl)
    yearly_min = bd['electricity_5yr_min'] / 5
    yearly_max = bd['electricity_5yr_max'] / 5
    print(f"   Yıllık elektrik: {yearly_min:,.0f} - {yearly_max:,.0f} TL/yıl")
    print(f"   5-yıl elektrik: {bd['electricity_5yr_min']:,.0f} - "
          f"{bd['electricity_5yr_max']:,.0f} TL arası")

   # Servis bilgisi
    service = tco.get("service_reliability")
    if service:
        print(f"\n🔧 SERVİS GÜVENİLİRLİĞİ:")
        print(f"   Seviye: {service['level']}")

        # Yeni field'lar
        if service.get('complaint_time_range'):
            print(f"   📅 Şikayet dönemi: {service['complaint_time_range']}")

        active_12m = service.get('active_complaints_last_12m')
        if active_12m is True:
            print(f"   ⚠️  Son 12 ay AKTİF şikayet")
        elif active_12m is False:
            print(f"   ✅ Son 12 ay aktif ciddi şikayet YOK")

        print(f"   Özet: {service['summary']}")
        if service.get('common_issues'):
            print(f"   Yaygın sorunlar:")
            for issue in service['common_issues'][:3]:
                print(f"      • {issue}")
    else:
        print(f"\n🔧 SERVİS: Bilgi yok")

    # Aksesuar önerileri
    accessories = tco.get("accessories_recommended", [])
    print(f"\n🎁 AKSESUAR ÖNERİLERİ ({len(accessories)}):")
    for a in accessories:
        importance_emoji = {
            "essential": "⭐",
            "recommended": "✅",
            "optional": "💡",
        }.get(a.get('importance', 'optional'), "💡")
        print(f"   {importance_emoji} {a['name']} ({a['price_range']}) - {a['importance']}")
        print(f"     {a['why_needed']}")

    # Coaching mesajı
    print(f"\n💬 COACHING MESAJI (preview):")
    print(tco.get("coaching_message", "")[:2500])
    print("...")


async def main():
    print("=" * 80)
    print("📊 TCO AGENT v3 TEST — Lean Honesty + Grounding")
    print("=" * 80)

    await test_scenario(
        "Samsung TV (G etiket)",
        "tv",
        "Samsung 55CU8000",
        23999,
    )

    print("\n💤 1 saniye bekle (cache test için)...")
    await asyncio.sleep(1)

    await test_scenario(
        "Philips TV (aksesuar cache hit beklenir)",
        "tv",
        "Philips 55PUS8050",
        25500,
    )

    print("\n💤 1 saniye bekle...")
    await asyncio.sleep(1)

    await test_scenario(
        "Gaming Laptop (laptop kategorisi)",
        "laptop",
        "Asus ROG Strix G16",
        45000,
    )

    print(f"\n{'=' * 80}")
    print("✅ Tüm testler tamamlandı")
    print('=' * 80)


if __name__ == "__main__":
    asyncio.run(main())