from google.adk.tools import ToolContext

from ...mcp_tools.google_map_mcp import maps_mcp


async def discover_places(
    destination: str,
    query: str,
    tool_context: ToolContext,
):
    """
    Search for multiple places to visit in a destination.

    Use this ONLY when the user wants place recommendations,
    sightseeing suggestions, attractions, museums, restaurants,
    parks, or other places to visit.

    Do NOT use this for questions about one specific place.
    For opening hours, entrance fees, phone numbers, addresses,
    websites, or ratings of a specific place, use get_place_details.
    """

    tools = await maps_mcp.get_tools()

    search_places = next(
        tool for tool in tools
        if tool.name == "search_places"
    )

    return await search_places.run_async(
        args={
            "textQuery": f"{query} in {destination}",
        },
        tool_context=tool_context,
    )