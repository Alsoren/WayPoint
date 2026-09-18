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