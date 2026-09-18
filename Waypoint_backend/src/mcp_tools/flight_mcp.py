import os
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)

api_key = os.environ.get("SERPAPI_API_KEY", "")

flight_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"https://mcp.serpapi.com/{api_key}/mcp",
        timeout=30,
    ),
    tool_filter=["search"],
)