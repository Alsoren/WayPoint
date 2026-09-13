"""Deterministic wrapper around weather_mcp's `search_location` +
`get_forecast`.

Why this exists: get_forecast has NO target-date parameter — it only
returns "the next N days from today" (max ~16). A trace showed
sightseeing_agent calling it anyway for a date ~11 months out; the tool
silently returned THIS week's forecast (since that's all it can ever
return), and the agent's own written instruction ("don't bother calling
get_forecast if the date is >16 days out") was not reliably followed by
the small model actually running it.

This wrapper does the date math in Python, not in the LLM's head: it
never calls get_forecast at all when the requested date falls outside
the tool's real window, so there is no way for a mismatched week's data
to reach the model in the first place.
"""

from datetime import date, datetime
from typing import Any

from google.adk.tools import ToolContext

from ..mcp_tools.weather import weather_mcp

MAX_FORECAST_DAYS = 16


def _extract_text(result: Any) -> tuple[str | None, str | None]:
    """Unwrap the MCP tool envelope, returning (text, error)."""
    if not isinstance(result, dict):
        return None, f"Unexpected response type: {type(result)}"
    if result.get("isError"):
        content = result.get("content") or []
        text = content[0].get("text") if content else None
        return None, text or "Tool reported isError=true with no message."
    content = result.get("content") or []
    if not content:
        return None, "Empty content in tool response."
    text = content[0].get("text")
    if not isinstance(text, str):
        return None, f"Unexpected content[0] shape: {content[0]!r}"
    return text, None


async def check_weather_full(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Check the real weather forecast for a trip, but ONLY if the trip
    actually falls within the forecast tool's real range (today to
    ~16 days out). Otherwise returns available=false immediately,
    without ever calling get_forecast — so a mismatched week's forecast
    can never be mistaken for the requested dates.

    Args:
        destination: City/place name to check weather for.
        check_in_date: Trip start date, ISO format (YYYY-MM-DD).
        check_out_date: Trip end date, ISO format (YYYY-MM-DD).
    """
    try:
        start = datetime.strptime(check_in_date, "%Y-%m-%d").date()
        end = datetime.strptime(check_out_date, "%Y-%m-%d").date()
    except ValueError as e:
        return {"available": False, "reason": f"Could not parse dates: {e}"}

    today = date.today()
    days_until_start = (start - today).days

    if days_until_start < 0:
        return {
            "available": False,
            "reason": (
                f"{check_in_date} is in the past relative to today "
                f"({today.isoformat()}) — no forecast to check."
            ),
        }

    if days_until_start > MAX_FORECAST_DAYS:
        return {
            "available": False,
            "reason": (
                f"{check_in_date} is {days_until_start} days from today "
                f"({today.isoformat()}); real forecasts only cover the "
                f"next {MAX_FORECAST_DAYS} days. No forecast exists yet "
                "for this trip — do not substitute another week's data "
                "or a general seasonal guess presented as a forecast."
            ),
        }

    days_needed = min(MAX_FORECAST_DAYS, (end - today).days + 1)
    days_needed = max(days_needed, days_until_start + 1)

    tools = await weather_mcp.get_tools()
    search_tool = next((t for t in tools if t.name == "search_location"), None)
    forecast_tool = next((t for t in tools if t.name == "get_forecast"), None)
    if search_tool is None or forecast_tool is None:
        return {"available": False, "reason": "Weather tools are not available."}

    loc_result = await search_tool.run_async(
        args={"query": destination}, tool_context=tool_context
    )
    loc_text, loc_error = _extract_text(loc_result)
    if loc_error is not None:
        return {"available": False, "reason": f"Location lookup failed: {loc_error}"}

    # search_location returns a numbered text list; take the first
    # "Coordinates: lat, lon" pair as the best match.
    import re

    match = re.search(r"Coordinates:\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)", loc_text)
    if not match:
        return {
            "available": False,
            "reason": f"Could not parse coordinates from location result: {loc_text[:200]}",
        }
    latitude, longitude = float(match.group(1)), float(match.group(2))

    forecast_result = await forecast_tool.run_async(
        args={
            "latitude": latitude,
            "longitude": longitude,
            "location": destination,
            "days": days_needed,
        },
        tool_context=tool_context,
    )
    forecast_text, forecast_error = _extract_text(forecast_result)
    if forecast_error is not None:
        return {"available": False, "reason": f"Forecast lookup failed: {forecast_error}"}

    return {
        "available": True,
        "raw_forecast": forecast_text,
        "requested_range": f"{check_in_date} to {check_out_date}",
    }