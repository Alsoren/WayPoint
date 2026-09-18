"""SerpApi MCP sunucusuna bağlanmayı iki farklı transport ile dener."""

import asyncio
import os
import traceback

from dotenv import load_dotenv

load_dotenv()

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    SseConnectionParams,
    StreamableHTTPConnectionParams,
)

api_key = os.environ.get("SERPAPI_API_KEY", "")
print(f"Key yüklendi mi: {bool(api_key)}")


async def try_connect(name: str, connection_params):
    print(f"\n--- {name} deneniyor ---")
    toolset = McpToolset(connection_params=connection_params, tool_filter=["search"])
    try:
        tools = await asyncio.wait_for(toolset.get_tools(), timeout=15)
        print(f"BAŞARILI: {len(tools)} tool döndü -> {[t.name for t in tools]}")
        return True
    except Exception as e:
        print(f"HATA: {type(e).__name__}: {e}")
        return False


async def main():
    url = f"https://mcp.serpapi.com/{api_key}/mcp"

    ok_streamable = await try_connect(
        "StreamableHTTPConnectionParams",
        StreamableHTTPConnectionParams(url=url, timeout=15),
    )
    if not ok_streamable:
        await try_connect("SseConnectionParams", SseConnectionParams(url=url, timeout=15))


if __name__ == "__main__":
    asyncio.run(main())