import asyncio
import json

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)


hotel_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mcp.vio.com/mcp",
        timeout=30,
    ),
    tool_filter=[
        "suggest_destinations",
        "search_hotels",
        "get_hotels",
        "search_hotels_availability",
    ],
)


async def main():
    tools = await hotel_mcp.get_tools()

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
            )
        )


if __name__ == "__main__":
    asyncio.run(main())