"""Waypoint'in weather_mcp nesnesini test eder (npx tabanlı stdio MCP server)."""

import asyncio
import sys
import traceback

sys.path.insert(0, "src")

from mcp_tools.weather import weather_mcp


async def main():
    print("--- weather_mcp.get_tools() çağrılıyor ---")
    try:
        tools = await asyncio.wait_for(weather_mcp.get_tools(), timeout=30)
        print(f"BAŞARILI: {len(tools)} tool döndü")
        for t in tools:
            print(f"  - {t.name}")
    except asyncio.TimeoutError:
        print("HATA: 30 saniyede yanıt gelmedi (timeout). npx paketi indiriyor olabilir, "
              "bir de terminalde manuel 'npx open-meteo-mcp-lite' çalıştırıp bekleyin.")
    except Exception as e:
        print(f"HATA TİPİ: {type(e).__name__}")
        print(f"HATA: {e}")
        print("\n--- Tam traceback ---")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())