from google.adk.tools import ToolContext

from ...mcp_tools.google_map_mcp import maps_mcp


async def get_place_details(
    place_name: str,
    destination: str,
    requested_info: str,
    tool_context: ToolContext,
):
    """
    Get factual information about ONE specific place.

    Use this when the user asks about a specific place's:
    opening hours, closing hours, entrance fee, ticket price,
    address, phone number, website, rating, or similar details.

    Also use this for follow-up questions about a place that was
    mentioned earlier in the conversation.

    Do NOT use this tool for:
    - directions
    - routes
    - distance between places
    - travel time
    - "how do I get there?" questions
    - call weather or search for general sightseeing places.

    Even if the request mentions one specific named place,
    route/directions requests must use the route tool instead.
    """

    tools = await maps_mcp.get_tools()

    search_places = next(
        tool for tool in tools
        if tool.name == "search_places"
    )

    query = f"{place_name} {destination} {requested_info}"

    return await search_places.run_async(
        args={
            "textQuery": query,
        },
        tool_context=tool_context,
    )