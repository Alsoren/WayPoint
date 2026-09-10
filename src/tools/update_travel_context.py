"""Extract travel updates and merge them into the current session.

Project contracts:
- run_agent(agent=..., message=..., tool_context=...) returns a dict or JSON str.
- ExtractionResult.updates is a Pydantic model with optional travel fields.
- ExtractionResult.clear_fields is a list of valid travel field names.
"""

import json
from typing import Any
from datetime import date
from google.adk.tools import ToolContext

from ..agent_runner import run_agent
from ..agents.extractor_agent import extractor_agent
from ..schemas import ExtractionResult


async def update_travel_context(
    message: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Extract and save travel details from the user's message.

    Args:
        message: The user's message containing new or changed travel details.
    """
    current_context = dict(tool_context.state.get("context", {}))

    # Include existing details so the extractor can interpret relative updates.
    current_date = date.today().isoformat()

    extraction_input = json.dumps(
        {
            "current_date": current_date,
            "user_message": message,
            "current_context": current_context,
        },
        ensure_ascii=False,
    )
    raw_result = await run_agent(
        agent=extractor_agent,
        message=extraction_input,
        tool_context=tool_context,
    )

    if isinstance(raw_result, str):
        result = ExtractionResult.model_validate_json(raw_result)
    else:
        result = ExtractionResult.model_validate(raw_result)

    # Omitted fields and nulls must not overwrite previously saved details.
    updates = result.updates.model_dump(
        exclude_unset=True, exclude_none=True, mode="json"
    )
    merged_context = {**current_context, **updates}

    # Explicit removals take precedence over updates.
    for field in result.clear_fields:
        merged_context.pop(field, None)

    tool_context.state["context"] = merged_context

    return {"status": "updated", "context": merged_context}