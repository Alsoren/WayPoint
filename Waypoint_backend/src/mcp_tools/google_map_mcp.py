import os
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)

# 1. Google Maps Grounding Lite MCP Tanımlaması
maps_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mapstools.googleapis.com/mcp",
        headers={
            # Demo anahtarını 'X-Goog-Api-Key' başlığı altında iletiyoruz
            "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_DEMO_KEY"),
        },
        timeout=30,
    ),
    tool_filter=[
        "search_places",
        "compute_routes",
        "lookup_weather",
    ],
)