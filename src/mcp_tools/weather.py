from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)
from mcp import StdioServerParameters


weather_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx.cmd",
            args=[
                "-y",
                "open-meteo-mcp-lite",
            ],
        )
    ),

    tool_filter=[
        "search_location",
        "get_weather",
        "get_forecast",
    ],
)