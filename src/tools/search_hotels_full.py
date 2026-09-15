"""Deterministic, multi-page hotel search wrapper.

Project contracts:
- Wraps the `search_hotels` MCP tool from hotel_mcp to fetch ALL pages
  (following `nextOffsets` while `hasMoreResults` is true) instead of
  relying on the LLM to decide whether/when to paginate.
- Requests prices explicitly in TRY via the `currency` param, so no
  manual currency conversion is ever needed - the budget (already TRY,
  as entered by the user) is compared directly against returned prices.
- Filters by budget in Python (not the LLM's own arithmetic), in
  addition to the upstream `filters.maxPrice` (which may return
  isPartialMatch hotels above budget - local filtering is the source
  of truth for what actually goes in `hotels_in_budget`).
- Scopes "already shown" hotel de-duplication to the specific search
  (destination + dates + travelers + area), so switching dates/city
  doesn't wrongly suppress hotels shown for a previous search.

Field names verified against https://developers.vio.com/mcp/reference/
search.html and /data-types.html.
"""

from datetime import datetime
from typing import Any

from google.adk.tools import ToolContext

from ..mcp_tools.hotel_mpc import hotel_mcp

MAX_PAGES = 5
PAGE_SIZE = 20


def _extract_hotel_id(hotel: dict[str, Any]) -> str | None:
  """Pull a stable identifier out of a hotel object."""
  for key in ("id", "hotelId", "propertyId", "code"):
    val = hotel.get(key)
    if val:
      return str(val).strip()
  name = hotel.get("name")
  return str(name).strip() if name else None


def _total_price(hotel: dict[str, Any]) -> float | None:
    offers = hotel.get("offers")

    if not isinstance(offers, dict):
        return None

    cheapest_rate = offers.get("cheapestRate")

    if not isinstance(cheapest_rate, dict):
        return None

    base = cheapest_rate.get("base")
    taxes = cheapest_rate.get("taxes")
    hotel_fees = cheapest_rate.get("hotelFees")

    parts = [base, taxes, hotel_fees]

    numeric = [
        float(value)
        for value in parts
        if isinstance(value, (int, float))
    ]

    if numeric:
        return sum(numeric)

    display_price = cheapest_rate.get("displayPrice")

    if display_price is not None:
        try:
            return float(display_price)
        except (TypeError, ValueError):
            pass

    return None


def _clean_hotel_for_llm(
    hotel: dict[str, Any], currency: str
) -> dict[str, Any]:
  """Strip a hotel down to only the fields the LLM needs, to save tokens."""
  location = hotel.get("location") or {}
  rating = hotel.get("rating") or {}
  classification = hotel.get("classification") or {}
  return {
      "id": _extract_hotel_id(hotel) or "unknown_id",
      "name": hotel.get("name") or "Bilinmeyen Otel",
      "total_price": _total_price(hotel),
      "currency": currency,
      "rating": rating.get("overall"),
      "star_rating": classification.get("starRating"),
      "area": location.get("address") or location.get("displayName"),
      "is_partial_match": hotel.get("isPartialMatch", False),
  }


def _extract_payload(result: Any) -> tuple[dict[str, Any] | None, str | None]:
  """Unwrap the MCP envelope. Prefers `structuredContent` (already
  parsed by the MCP layer) and falls back to parsing `content[0].text`
  as JSON when structuredContent isn't present."""
  if not isinstance(result, dict):
    return None, f"Unexpected response type: {type(result)}"

  content = result.get("content") or []
  if result.get("isError"):
    text = content[0].get("text") if content else None
    return None, text or "Tool call failed with no message."

  structured = result.get("structuredContent")
  if isinstance(structured, dict):
    return structured, None

  if not content:
    return None, "Empty content in tool response."

  text = content[0].get("text")
  if not isinstance(text, str):
    return None, f"Unexpected content[0] shape: {content[0]!r}"

  import json

  try:
    payload = json.loads(text)
  except json.JSONDecodeError as e:
    return None, f"Could not parse tool response JSON: {e}"

  if not isinstance(payload, dict):
    return None, f"Parsed payload is not an object: {type(payload)}"

  return payload, None


async def search_hotels_full(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    travelers: int,
    total_budget: float | None,
    tool_context: ToolContext,
    preferred_hotel_area: str | None = None,
    min_star_rating: int | None = None,
) -> dict[str, Any]:
  """Search hotels across ALL pages, in TRY, filtered by budget locally.

  Args:
      destination: City to search hotels in.
      check_in_date: Check-in date, YYYY-MM-DD.
      check_out_date: Check-out date, YYYY-MM-DD.
      travelers: Number of adult travelers (single room).
      total_budget: Total stay budget in TRY, if given. Compared
          directly against returned prices - no currency conversion,
          since prices are requested in TRY explicitly.
      preferred_hotel_area: Specific neighborhood, if any.
      min_star_rating: Minimum star rating filter (1-5), if any.
  """
  tools = await hotel_mcp.get_tools()
  search_tool = next((t for t in tools if t.name == "search_hotels"), None)
  if search_tool is None:
    return {"error": "search_hotels tool is not available."}

  query_text = (
      f"{preferred_hotel_area}, {destination}"
      if preferred_hotel_area
      else destination
  )

  filters: dict[str, Any] = {}
  if total_budget is not None:
    filters["maxPrice"] = round(total_budget, 2)
  if min_star_rating is not None and 1 <= min_star_rating <= 5:
    filters["starRatings"] = list(range(min_star_rating, 6))

  base_args: dict[str, Any] = {
      "queries": [query_text],
      "checkIn": check_in_date,
      "checkOut": check_out_date,
      "rooms": {"adults": travelers},
      "currency": "TRY",
      "priceMode": "total",
      "searchMode": "deep",
      "include": [
          "location",
          "rating",
          "classification",
          "offer",
      ],
      "offers": {
          "mode": "cheapest",
      },
      "sortField": "price",
      "sortOrder": "ascending",
      "pageSize": PAGE_SIZE,
  }
  if filters:
    base_args["filters"] = filters

  all_hotels: list[dict[str, Any]] = []
  seen_ids: set[str] = set()
  offsets: list[int] | None = None
  pages_fetched = 0
  last_error: str | None = None
  response_currency = "TRY"

  while pages_fetched < MAX_PAGES:
    args = dict(base_args)
    if offsets:
      args["offsets"] = offsets

    raw_result = await search_tool.run_async(
        args=args, tool_context=tool_context
    )
    pages_fetched += 1

    payload, error = _extract_payload(raw_result)
    if error is not None:
      last_error = error
      break

    response_currency = payload.get("currency", response_currency)

    for hotel in payload.get("hotels") or []:
      hotel_id = _extract_hotel_id(hotel)
      if hotel_id and hotel_id in seen_ids:
        continue
      if hotel_id:
        seen_ids.add(hotel_id)
      all_hotels.append(hotel)

    if not payload.get("hasMoreResults"):
      break
    next_offsets = payload.get("nextOffsets") or []
    if not next_offsets:
      break
    offsets = next_offsets

  priced = [(h, _total_price(h)) for h in all_hotels]
  priced_known = [(h, p) for h, p in priced if p is not None]

  cheapest: dict[str, Any] | None = None
  if priced_known:
    cheapest_hotel = min(priced_known, key=lambda hp: hp[1])[0]
    cheapest = _clean_hotel_for_llm(cheapest_hotel, response_currency)

  if total_budget is not None:
    in_budget_hotels = [
        h for h, p in priced_known
        if p <= total_budget and not h.get("isPartialMatch")
    ]
  else:
    in_budget_hotels = [h for h, _ in priced_known]

  # Scope "already shown" tracking to this exact search so a different
  # city/date/traveler search doesn't get wrongly suppressed.
  search_key = "|".join([
      destination, check_in_date, check_out_date,
      str(travelers), str(preferred_hotel_area), str(min_star_rating),
  ])
  hotel_search_state = tool_context.state.get("_hotel_search_state") or {}
  if hotel_search_state.get("search_key") != search_key:
    hotel_search_state = {"search_key": search_key, "shown_ids": []}
  shown_ids = set(hotel_search_state.get("shown_ids", []))

  fresh_hotels = [
      h for h in in_budget_hotels
      if (hid := _extract_hotel_id(h)) and hid not in shown_ids
  ]

  summary = [
      _clean_hotel_for_llm(h, response_currency) for h in fresh_hotels[:8]
  ]
  for h in summary:
    if h["id"] != "unknown_id":
      shown_ids.add(h["id"])

  tool_context.state["_hotel_search_state"] = {
      "search_key": search_key,
      "shown_ids": list(shown_ids),
  }

  return {
      "hotels_in_budget": summary,
      "cheapest_hotel_fallback": cheapest,
      "total_matched": len(in_budget_hotels),
      "total_scanned": len(all_hotels),
      "pages_fetched": pages_fetched,
      "currency": response_currency,
      "error": last_error,
  }