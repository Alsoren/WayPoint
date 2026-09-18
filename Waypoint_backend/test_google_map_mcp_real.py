import asyncio
import json
import os

from dotenv import load_dotenv

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)


# .env dosyasını ÖNCE yükle
load_dotenv()


EXPECTED_TOOLS = {
    "search_places",
    "compute_routes",
    "lookup_weather",
}


maps_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mapstools.googleapis.com/mcp",
        headers={
            "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_DEMO_KEY"),
        },
        timeout=30,
    ),
    tool_filter=list(EXPECTED_TOOLS),
)


async def main():
    api_key = os.getenv("GOOGLE_MAPS_DEMO_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_MAPS_DEMO_KEY environment variable is not set."
        )

    print("✓ API key .env dosyasından yüklendi.")
    print("Google Maps MCP'ye bağlanılıyor...\n")

    tools = await maps_mcp.get_tools()

    loaded_tool_names = {tool.name for tool in tools}

    print("Loaded tools:")

    for name in loaded_tool_names:
        print(f"  ✓ {name}")

    missing_tools = EXPECTED_TOOLS - loaded_tool_names

    if missing_tools:
        print("\nMissing tools:")

        for name in missing_tools:
            print(f"  ✗ {name}")

    else:
        print("\n✓ Bütün beklenen tool'lar başarıyla yüklendi.")

    for tool in tools:
        print("\n" + "=" * 60)
        print(f"TOOL: {tool.name}")
        print("=" * 60)

        schema = getattr(tool, "input_schema", None)

        print(
            json.dumps(
                schema,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())