import json
from typing import Any

from google.adk.tools import ToolContext

from ..mcp_tools.hotel_mpc import hotel_mcp


def _extract_payload(
    result: Any,
) -> tuple[dict[str, Any] | None, str | None]:

    if not isinstance(result, dict):
        return None, f"Unexpected response type: {type(result)}"

    content = result.get("content") or []

    if result.get("isError"):
        text = (
            content[0].get("text")
            if content and isinstance(content[0], dict)
            else None
        )

        return None, text or "Hotel tool failed."

    structured = result.get("structuredContent")

    if isinstance(structured, dict):
        return structured, None

    if not content:
        return None, "Empty hotel tool response."

    first = content[0]

    if not isinstance(first, dict):
        return None, "Unexpected hotel tool content."

    text = first.get("text")

    if not isinstance(text, str):
        return None, "Hotel tool returned no readable content."

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"Could not parse hotel response: {exc}"

    if not isinstance(payload, dict):
        return None, "Hotel response is not an object."

    return payload, None


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _extract_amenities(
    hotel: dict[str, Any],
) -> list[str]:

    facilities = hotel.get("facilities") or {}

    if not isinstance(facilities, dict):
        return []

    amenities: list[str] = []

    items = facilities.get("items") or []

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name")

        if name and name not in amenities:
            amenities.append(str(name))

    for key in ("amenities", "business", "dining"):
        value = facilities.get(key)

        if isinstance(value, str) and value.strip():
            amenities.append(value.strip())

    return amenities


def _extract_price(
    hotel: dict[str, Any],
) -> tuple[float | None, str | None]:

    offers = hotel.get("offers") or {}

    if not isinstance(offers, dict):
        return None, None

    rate = offers.get("cheapestRate")

    if not isinstance(rate, dict):
        return None, None

    display_price = rate.get("displayPrice")

    try:
        price = (
            float(display_price)
            if display_price is not None
            else None
        )
    except (TypeError, ValueError):
        price = None

    items = offers.get("items") or []

    currency = None

    if items and isinstance(items[0], dict):
        currency = items[0].get("currency")

    return price, currency


async def get_hotel_details(
    hotel_name: str,
    requested_info: str,
    tool_context: ToolContext,
    hotel_id: str | None = None,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
    travelers: int | None = None,
) -> dict[str, Any]:
    """
    Retrieve verified details about one specific hotel.

    Use this when the user asks about a specific hotel's amenities,
    breakfast, WiFi, parking, policies, check-in/check-out information,
    rating, star rating, address, phone number, or similar details.

    If hotel_id is unavailable, the hotel name is resolved first.

    requested_info should describe exactly what the user wants.
    """

    tools = await hotel_mcp.get_tools()

    get_hotels_tool = next(
        (
            tool
            for tool in tools
            if tool.name == "get_hotels"
        ),
        None,
    )

    suggest_tool = next(
        (
            tool
            for tool in tools
            if tool.name == "suggest_destinations"
        ),
        None,
    )

    if get_hotels_tool is None:
        return {
            "status": "error",
            "error": "get_hotels tool is unavailable.",
        }

    # -------------------------------------------------
    # Resolve hotel ID when only a hotel name is known
    # -------------------------------------------------

    if not hotel_id:

        if suggest_tool is None:
            return {
                "status": "error",
                "error": "Hotel resolution tool is unavailable.",
            }

        raw_suggestions = await suggest_tool.run_async(
            args={
                "query": hotel_name,
                "limit": 5,
            },
            tool_context=tool_context,
        )

        suggestion_payload, error = _extract_payload(
            raw_suggestions
        )

        if error:
            return {
                "status": "error",
                "error": error,
            }

        suggestions = (
            suggestion_payload.get("suggestions")
            or []
        )

        hotel_candidates = [
            item
            for item in suggestions
            if (
                isinstance(item, dict)
                and item.get("type") == "hotel"
            )
        ]

        if not hotel_candidates:
            return {
                "status": "not_found",
                "hotel_name": hotel_name,
                "message": "Hotel could not be resolved.",
            }

        normalized_requested = _normalize_name(
            hotel_name
        )

        exact_matches = [
            item
            for item in hotel_candidates
            if _normalize_name(
                str(item.get("name", ""))
            ) == normalized_requested
        ]

        if len(exact_matches) == 1:
            selected = exact_matches[0]

        elif len(hotel_candidates) == 1:
            selected = hotel_candidates[0]

        else:
            return {
                "status": "needs_clarification",
                "hotel_name": hotel_name,
                "candidates": [
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "location": item.get(
                            "placeDisplayName"
                        ),
                    }
                    for item in hotel_candidates[:5]
                ],
            }

        hotel_id = str(selected["id"])

    # -------------------------------------------------
    # Decide what hotel information to fetch
    # -------------------------------------------------

    include = [
        "location",
        "rating",
        "classification",
        "facilities",
        "policies",
        "faq",
    ]

    lower_request = requested_info.casefold()

    wants_price = any(
        word in lower_request
        for word in (
            "price",
            "fee",
            "cost",
            "ücret",
            "fiyat",
            "availability",
            "müsait",
        )
    )

    if wants_price:
        include.append("offers")

    args: dict[str, Any] = {
        "hotelIds": [hotel_id],
        "include": include,
    }

    # Price/availability only makes sense with dates.
    if check_in_date:
        args["checkIn"] = check_in_date

    if check_out_date:
        args["checkOut"] = check_out_date

    if travelers:
        args["roomsConfiguration"] = [
            {
                "adults": travelers,
            }
        ]

    raw_result = await get_hotels_tool.run_async(
        args=args,
        tool_context=tool_context,
    )

    payload, error = _extract_payload(raw_result)

    if error:
        return {
            "status": "error",
            "error": error,
        }

    hotels = payload.get("hotels") or []

    if not hotels:
        return {
            "status": "not_found",
            "hotel_name": hotel_name,
            "hotel_id": hotel_id,
        }

    hotel = hotels[0]

    location = hotel.get("location") or {}
    rating = hotel.get("rating") or {}
    classification = (
        hotel.get("classification") or {}
    )
    policies = hotel.get("policies") or {}

    total_price, currency = _extract_price(
        hotel
    )

    return {
        "status": "completed",

        "id": hotel.get("id"),
        "name": hotel.get("name"),

        "location": (
            location.get("address")
            or location.get("displayName")
        ),

        "rating": rating.get("overall"),

        "star_rating": classification.get(
            "starRating"
        ),

        "phone": hotel.get("phone"),

        "property_description": hotel.get(
            "propertyDescription"
        ),

        "rooms_description": hotel.get(
            "roomsDescription"
        ),

        "amenities": _extract_amenities(
            hotel
        ),

        "policies": policies,

        "faq": hotel.get("faq") or [],

        "total_price": total_price,

        "currency": currency,

        "requested_info": requested_info,
    }