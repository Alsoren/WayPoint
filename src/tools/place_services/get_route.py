from google.adk.tools import ToolContext

from ...mcp_tools.google_map_mcp import maps_mcp


async def get_route(
    origin: str,
    destination: str,
    tool_context: ToolContext,
    travel_mode: str = "DRIVE",
):
    """
    Get route information between two places.

    Use this when the user asks:
    - how to get somewhere
    - directions
    - travel time
    - distance
    - "how do I get there?"
    - "give me directions"
    - "how long does it take?"
    - "how many minutes does it take?"

    Do NOT use get_place_details for route requests.
    """

    tools = await maps_mcp.get_tools()

    route_tool = next(
        tool for tool in tools
        if tool.name == "compute_routes"
    )

    args = {
        "origin": {
            "address": origin,
        },
        "destination": {
            "address": destination,
        },
        "travelMode": travel_mode,
    }

    return await route_tool.run_async(
        args=args,
        tool_context=tool_context,
    )