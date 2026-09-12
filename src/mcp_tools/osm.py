from google.adk.tools.mcp_tool import McpToolset

from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)

from mcp import StdioServerParameters

#özellikle 'attraction' ve 'museum' gibi geniş/karmaşık Overpass sorgusu gerektiren kategorilerde sürekli timeout oluyor sonradan bak

osm_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx.cmd",
            args=[
                "-y",
                "osm-mcp",
            ],
        ),
        timeout=30,
    ),

    tool_filter=[
        "geocode",
        "find_nearby_pois",
        "route",
        "route_matrix",
        "poi_details",
    ],
)