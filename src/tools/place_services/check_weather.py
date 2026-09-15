from datetime import date

from google.adk.tools import ToolContext

from ...mcp_tools.google_map_mcp import maps_mcp


async def check_weather(
    destination: str,
    travel_date: str | None,
    tool_context: ToolContext,
):
    """
    Get weather information for a destination.

    Use this ONLY when:
    - the user explicitly asks about weather, or
    - weather is useful for choosing sightseeing recommendations.

    Do NOT use this for questions about a specific place such as
    opening hours, entrance fees, address, phone number, or website.
    """

    tools = await maps_mcp.get_tools()

    lookup_weather = next(
        tool for tool in tools
        if tool.name == "lookup_weather"
    )

    args = {
        "location": {
            "address": destination,
        }
    }

    if travel_date:
        requested_date = date.fromisoformat(travel_date)
        days_until = (requested_date - date.today()).days

        if not 0 <= days_until <= 9:
            return {
                "available": False,
                "reason": "Requested date is outside the supported forecast range.",
            }

        args["date"] = {
            "year": requested_date.year,
            "month": requested_date.month,
            "day": requested_date.day,
        }

    return await lookup_weather.run_async(
        args=args,
        tool_context=tool_context,
    )