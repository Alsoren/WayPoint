import asyncio
import json
from typing import Any

from google.adk.tools import ToolContext

from ..agent_runner import run_agent
from ..agents.flight_agent import flight_agent
from ..agents.hotel_agent import hotel_agent
from ..agents.sightseeing_agent import sightseeing_agent


AGENT_REGISTRY = {
    "flight": flight_agent,
    "hotel": hotel_agent,
    "sightseeing": sightseeing_agent,
}


REQUIRED_FIELDS = {
    "flight": [
        "origin",
        "destination",
        "departure_date",
        "travelers",
    ],
    "hotel": [
        "destination",
        "check_in_date",
        "check_out_date",
        "travelers",
    ],
    "sightseeing": [
        "destination",
    ],
}


def validate_agent_data(
    agent_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Ajan için gerekli alanların mevcut olup olmadığını kontrol eder."""

    if agent_type not in AGENT_REGISTRY:
        return {
            "is_valid": False,
            "error": f"Bilinmeyen ajan türü: {agent_type}",
            "missing_fields": [],
        }

    required_fields = REQUIRED_FIELDS[agent_type]
    missing_fields = []

    for field in required_fields:
        value = data.get(field)

        if value is None:
            missing_fields.append(field)
        elif isinstance(value, str) and not value.strip():
            missing_fields.append(field)

    if missing_fields:
        return {
            "is_valid": False,
            "agent_type": agent_type,
            "missing_fields": missing_fields,
            "message": (
                f"{agent_type} araması için eksik bilgiler var: "
                f"{', '.join(missing_fields)}"
            ),
        }

    return {
        "is_valid": True,
        "agent_type": agent_type,
        "agent": AGENT_REGISTRY[agent_type],
    }


async def search_travel(
    tasks: list[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    context = tool_context.state.get("context", {})

    context_message = json.dumps(
        {
            "travel_context": context,
            "instruction": (
                "Search according to this travel context "
                "and return structured results."
            ),
        },
        ensure_ascii=False,
    )

    for task in tasks:
        validation = validate_agent_data(
            agent_type=task,
            data=context,
        )

        if not validation["is_valid"]:
            return {
                "status": "needs_input",
                "task": task,
                "missing_fields": validation.get("missing_fields", []),
                "message": validation.get(
                    "message",
                    validation.get("error", "Geçersiz arama görevi."),
                ),
            }

    outputs = await asyncio.gather(
        *[
            run_agent(
                agent=AGENT_REGISTRY[task],
                message=context_message,
                tool_context=tool_context,
            )
            for task in tasks
        ]
    )

    results = dict(zip(tasks, outputs))

    return {
        "status": "completed",
        "results": results,
    }