"""Deterministic wrapper around SerpApi's `search` (engine=google_flights)
tool from flight_mcp.

Why this exists (same rationale as search_hotels_full.py):
- Forces the required parameters (currency, correct airport codes) on
  every call instead of relying on the LLM to remember them each turn.
  A trace showed the raw SerpApi response for one single flight search
  contains: 60 historical price points (price_insights.price_history),
  2 images per airport (airports[].departure/arrival.image/.thumbnail),
  a logo PNG per flight (airline_logo, repeated per option), and several
  internal debug links (raw_html_file, prettify_html_file,
  markdown_endpoint, json_endpoint). None of that is usable by a text
  LLM, but all of it gets fed into context on every single search if the
  raw tool response is passed through unmodified — this is the same
  failure mode that exhausted the Gemini free-tier quota (429) earlier.
  This wrapper strips the response down to only the fields actually
  needed to answer the user, before it ever reaches the LLM.

Real `search` tool input shape: {"params": {...engine-specific fields...}}
Real MCP envelope: {"content": [{"type": "text", "text": "<json string>"}],
"isError": bool} — same as hotel_mcp, the actual SerpApi payload is
JSON-encoded INSIDE content[0]["text"].
"""

import json
from typing import Any

from google.adk.tools import ToolContext

from ..mcp_tools.flight_mcp import flight_mcp


def _extract_payload(result: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Unwrap the MCP tool envelope and parse the JSON text inside it."""
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

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"Could not parse tool response JSON: {e}"

    if not isinstance(payload, dict):
        return None, f"Parsed payload is not an object: {type(payload)}"

    return payload, None


def _trim_flight_group(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the fields actually useful to the agent/user.

    Drops: airline_logo, carbon_emissions detail (kept as a single
    percent), legroom/extensions marketing text, plane_and_crew_by,
    travel_class detail beyond the value itself.
    """
    trimmed = []
    for option in group:
        legs = option.get("flights") or []
        trimmed_legs = []
        for leg in legs:
            dep = leg.get("departure_airport") or {}
            arr = leg.get("arrival_airport") or {}
            trimmed_legs.append(
                {
                    "airline": leg.get("airline"),
                    "flight_number": leg.get("flight_number"),
                    "departure_airport": {
                        "id": dep.get("id"),
                        "name": dep.get("name"),
                        "time": dep.get("time"),
                    },
                    "arrival_airport": {
                        "id": arr.get("id"),
                        "name": arr.get("name"),
                        "time": arr.get("time"),
                    },
                    "duration_minutes": leg.get("duration"),
                    "travel_class": leg.get("travel_class"),
                }
            )
        trimmed.append(
            {
                "flights": trimmed_legs,
                "total_duration_minutes": option.get("total_duration"),
                "price": option.get("price"),
                "type": option.get("type"),
                "departure_token": option.get("departure_token"),
            }
        )
    return trimmed


async def search_flights_full(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    currency: str,
    tool_context: ToolContext,
    return_date: str | None = None,
    departure_token: str | None = None,
) -> dict[str, Any]:
    """Search flights via SerpApi (engine=google_flights) and return a
    trimmed, token-cheap result.

    Args:
        departure_id: Departure airport code (e.g. "SAW").
        arrival_id: Arrival airport code (e.g. "ESB").
        outbound_date: Outbound date, ISO format (YYYY-MM-DD).
        currency: Currency code (e.g. "TRY"). Always pass the travel
            context's currency here — never omit it, SerpApi silently
            defaults to USD otherwise.
        return_date: Return date, ISO format (YYYY-MM-DD), for round
            trips. Omit for one-way searches.
        departure_token: Token from a previously returned outbound flight
            option, required to fetch that option's specific return
            flights. Omit when searching the outbound leg.
    """
    tools = await flight_mcp.get_tools()
    search_tool = next((t for t in tools if t.name == "search"), None)
    if search_tool is None:
        return {"error": "search tool is not available."}

    params: dict[str, Any] = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "currency": currency,
        "type": "1" if return_date else "2",  # 1=round trip, 2=one way
    }
    if return_date:
        params["return_date"] = return_date
    if departure_token:
        params["departure_token"] = departure_token

    raw_result = await search_tool.run_async(
        args={"params": params}, tool_context=tool_context
    )

    payload, error = _extract_payload(raw_result)
    if error is not None:
        return {"error": error}

    price_insights = payload.get("price_insights") or {}

    return {
        "best_flights": _trim_flight_group(payload.get("best_flights") or []),
        "other_flights": _trim_flight_group(payload.get("other_flights") or []),
        "lowest_price": price_insights.get("lowest_price"),
        "price_level": price_insights.get("price_level"),
        "currency": currency,
        "google_flights_url": (payload.get("search_metadata") or {}).get(
            "google_flights_url"
        ),
    }