"""Deterministic wrapper around weather_mcp's `search_location` +
`get_forecast`.

Why this exists: get_forecast has NO target-date parameter — it only
returns "the next N days from today" (max ~16), with no way to skip
straight to a single future day. A trace showed sightseeing_agent
calling it anyway for a date ~11 months out; the tool silently returned
THIS week's forecast (since that's all it can ever return), and the
agent's own written instruction ("don't bother calling get_forecast if
the date is >16 days out") was not reliably followed by the small model
actually running it.

This wrapper does the date math in Python, not in the LLM's head: it
never calls get_forecast at all when the requested date falls outside
the tool's real window. It also fixes a second issue: since the
underlying tool can only return a block starting from TODAY, asking
about a single day still requires fetching every day in between — but
there is no reason to hand all of those intervening days to the model
too. This wrapper slices the response down to just the requested
date(s) before returning, so a single-day question gets a single day's
answer, not a full week dumped on top of it.
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


def _slice_days(forecast_text: str, start_index: int, end_index: int) -> str:
    """The tool returns one block of text per day, starting with today
    (index 0), separated by blank lines, after a one-line title. Slice
    out only the blocks for [start_index, end_index] (inclusive) so a
    single-day question doesn't drag the intervening days along too.
    """
    parts = forecast_text.split("\n\n")
    if not parts:
        return forecast_text
    title, day_blocks = parts[0], parts[1:]
    wanted = day_blocks[start_index : end_index + 1]
    if not wanted:
        return forecast_text  # fall back to returning everything
    return title + "\n\n" + "\n\n".join(wanted)


async def check_weather_full(
    destination: str,
    date_from: str,
    tool_context: ToolContext,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Check the real weather forecast for one date, or a date range,
    but ONLY if it actually falls within the forecast tool's real range
    (today to ~16 days out). Otherwise returns available=false
    immediately, without ever calling get_forecast — so a mismatched
    week's forecast can never be mistaken for the requested date(s).
    Returns only the requested date(s), not every day in between.

    Args:
        destination: City/place name to check weather for.
        date_from: The date to check, ISO format (YYYY-MM-DD). Use this
            alone for a single-day question ("what's the weather on the
            18th") — there is no need to also know a checkout/return
            date just to check weather for one day.
        date_to: Optional end of a date range (ISO format), if checking
            weather across multiple days (e.g. a whole trip). Omit for
            a single-day check — it defaults to date_from.
    """
    date_to = date_to or date_from

    try:
        start = datetime.strptime(date_from, "%Y-%m-%d").date()
        end = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as e:
        return {"available": False, "reason": f"Could not parse dates: {e}"}

    today = date.today()
    days_until_start = (start - today).days
    days_until_end = (end - today).days

    if days_until_start < 0:
        return {
            "available": False,
            "reason": (
                f"{date_from} is in the past relative to today "
                f"({today.isoformat()}) — no forecast to check."
            ),
        }

    if days_until_start > MAX_FORECAST_DAYS:
        return {
            "available": False,
            "reason": (
                f"{date_from} is {days_until_start} days from today "
                f"({today.isoformat()}); real forecasts only cover the "
                f"next {MAX_FORECAST_DAYS} days. No forecast exists yet "
                "for this date — do not substitute another day's data "
                "or a general seasonal guess presented as a forecast."
            ),
        }

    days_needed = min(MAX_FORECAST_DAYS, days_until_end + 1)

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

    sliced = _slice_days(forecast_text, days_until_start, days_until_end)

    return {
        "available": True,
        "raw_forecast": sliced,
        "requested_range": f"{date_from} to {date_to}" if date_to != date_from else date_from,
    }