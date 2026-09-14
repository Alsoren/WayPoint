"""Deterministic, sequential wrapper around osm_mcp's `find_nearby_pois`.

Why this exists:
A trace showed sightseeing_agent calling find_nearby_pois for two
categories (e.g. "attraction" and "museum") within ~0.2ms of each other —
i.e. in parallel, dispatched from a single LLM turn requesting two tool
calls at once. The public Overpass API backing osm-mcp allows only ~2
concurrent request slots per IP; two parallel category searches compete
for those same slots (alongside whatever other public traffic is
hitting the same shared Overpass instance), and the resulting queueing
delay routinely exceeds the client-side timeout — even though every
category's Overpass query is identical in structure and cost
(`nwr[tag](around:radius,lat,lon); out center tags LIMIT;` — verified in
osm-mcp's own source, so no category is inherently "heavier" than
another). A single, unparalleled category search reliably succeeds fast.

This wrapper removes the LLM's ability to fire those calls in parallel:
it awaits each category's find_nearby_pois call one at a time, in
Python, before starting the next. If a category times out or errors, it
is not retried — the wrapper moves on to the next requested category
(or an optional fallback category) instead of burning more time on a
category that just failed.
"""

import asyncio
from typing import Any

from google.adk.tools import ToolContext

from ..mcp_tools.osm import osm_mcp

# How long to wait for a single category before giving up on it and
# moving to a fallback. A live trace showed "attraction"/"museum" both
# failing back-to-back at 45s each (~90s wasted before even reaching a
# working fallback category, ~2 minutes total for the whole tool call).
# Lowered to 18s: real Overpass timeouts/queue failures for these dense
# tags have consistently shown up well under that in practice, and a
# category that hasn't answered by 18s is not going to suddenly recover
# — cutting our own wait short gets to a working fallback much faster
# without meaningfully increasing the odds of abandoning a call that
# would have succeeded.
PER_CATEGORY_TIMEOUT_S = 18


def _extract_payload(result: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Unwrap the MCP tool envelope and parse the JSON text inside it."""
    if not isinstance(result, dict):
        return None, f"Unexpected response type: {type(result)}"

    if result.get("isError"):
        content = result.get("content") or []
        text = content[0].get("text") if content else None
        return None, text or "Tool reported isError=true with no message."

    # find_nearby_pois returns structuredContent directly alongside the
    # text envelope; prefer it when present (already-parsed dict).
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured, None

    content = result.get("content") or []
    if not content:
        return None, "Empty content in tool response."

    text = content[0].get("text")
    if not isinstance(text, str):
        return None, f"Unexpected content[0] shape: {content[0]!r}"

    # The text may be prefixed with an "untrusted data" notice before the
    # JSON body (osm-mcp does this deliberately) — find the JSON object.
    brace_index = text.find("{")
    if brace_index == -1:
        return None, f"No JSON object found in tool text: {text[:200]!r}"

    import json

    try:
        payload = json.loads(text[brace_index:])
    except json.JSONDecodeError as e:
        return None, f"Could not parse tool response JSON: {e}"

    if not isinstance(payload, dict):
        return None, f"Parsed payload is not an object: {type(payload)}"

    return payload, None


async def search_places_full(
    near: str,
    categories: list[str],
    tool_context: ToolContext,
    radius_m: int = 1200,
    limit_per_category: int = 5,
    fallback_categories: list[str] | None = None,
) -> dict[str, Any]:
    """Search OSM for points of interest across multiple categories,
    calling find_nearby_pois SEQUENTIALLY (never in parallel) to avoid
    contending with Overpass's per-IP concurrency limit.

    Args:
        near: Place name, address, or "lat,lon" coordinates.
        categories: Category shortcuts to search, in priority order
            (e.g. ["attraction", "museum"]). Searched one at a time.
        radius_m: Search radius in meters. Clamped to 50-2500 (NOT
            10000 — see note below). Default 1200 (deliberately small)
            — a live trace showed dense tags like
            "attraction"/"museum"/"monument"/"viewpoint" in a historic
            city center returning so many matching OSM elements within
            a 3000m radius that Overpass's own internal timeout was hit
            before it could even respond with an error, costing ~25s
            per failed category. The upper clamp is capped at 2500 (down
            from a looser 10000) specifically because the model has been
            observed passing radius_m=3000 anyway, defeating the
            small-default intent — capping the ceiling, not just the
            default, is what actually prevents that. Widen only as a
            deliberate follow-up if results come back too sparse - never
            start wide.
        limit_per_category: Max results per category. Clamped to 1-25.
        fallback_categories: If a category in `categories` errors or
            times out, try the next unused category from this list
            instead (skipping it, not retrying the failed one). Pass
            categories known to be lower-risk, e.g. ["park", "viewpoint",
            "monument"].
    """
    radius_m = max(50, min(2500, radius_m))
    limit_per_category = max(1, min(25, limit_per_category))

    tools = await osm_mcp.get_tools()
    find_tool = next((t for t in tools if t.name == "find_nearby_pois"), None)
    if find_tool is None:
        return {"error": "find_nearby_pois tool is not available."}

    fallback_pool = list(fallback_categories or [])
    results_by_category: dict[str, Any] = {}
    errors: dict[str, str] = {}
    all_places: list[dict[str, Any]] = []
    seen_osm_ids: set[str] = set()

    queue = list(categories)

    while queue:
        category = queue.pop(0)

        try:
            raw_result = await asyncio.wait_for(
                find_tool.run_async(
                    args={
                        "near": near,
                        "category": category,
                        "radius_m": radius_m,
                        "limit": limit_per_category,
                    },
                    tool_context=tool_context,
                ),
                timeout=PER_CATEGORY_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            errors[category] = "timed out"
            if fallback_pool:
                queue.append(fallback_pool.pop(0))
            continue

        payload, error = _extract_payload(raw_result)
        if error is not None:
            errors[category] = error
            if fallback_pool:
                queue.append(fallback_pool.pop(0))
            continue

        places = payload.get("results") or []
        results_by_category[category] = {
            "count": payload.get("count", len(places)),
            "note": payload.get("note"),
        }
        for place in places:
            osm_id = place.get("osm")
            if osm_id and osm_id in seen_osm_ids:
                continue
            if osm_id:
                seen_osm_ids.add(osm_id)
            all_places.append({**place, "category": category})

    return {
        "places": all_places,
        "categories_searched": list(results_by_category.keys()),
        "categories_failed": errors,
    }