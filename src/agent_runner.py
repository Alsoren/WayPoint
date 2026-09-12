"""Call an agent from a Python tool and return its output."""

import asyncio
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.genai.errors import ClientError
from pydantic import BaseModel, ValidationError


def _extract_retry_delay_seconds(error: ClientError, default: float) -> float:
    """Pull Google's suggested retry delay out of a 429 error, if present."""
    try:
        details = error.details.get("error", {}).get("details", [])
        for entry in details:
            if entry.get("@type", "").endswith("RetryInfo"):
                raw = entry.get("retryDelay", "")
                if raw.endswith("s"):
                    return float(raw[:-1])
    except Exception:
        pass
    return default


async def run_agent(
    agent: LlmAgent,
    message: str,
    tool_context: ToolContext,
    max_attempts: int = 2,
    max_quota_retries: int = 2,
) -> dict[str, Any] | str:
    """Run an agent without input_schema using the active tool context.

    AgentTool may propagate child state changes to the caller. Keep the
    extractor free of state-writing tools, callbacks and output_key; its
    caller is responsible for merging the extracted travel updates.

    Retries once if the agent's structured output fails schema validation
    (small models occasionally break the JSON contract on long or
    multi-step tool-use turns) by asking it to resend the same result as
    strict JSON.

    Separately retries on 429 RESOURCE_EXHAUSTED quota errors, honoring
    Google's suggested retryDelay, up to max_quota_retries times. If the
    quota error persists, raises a clean, user-safe RuntimeError instead
    of letting the raw API exception surface to the caller.
    """
    if agent.input_schema is not None:
        raise ValueError("run_agent expects an agent without input_schema.")

    agent_tool = AgentTool(agent=agent)

    last_error: Exception | None = None
    attempt_message = message
    quota_retries_left = max_quota_retries

    for attempt in range(1, max_attempts + 1):
        try:
            result = await agent_tool.run_async(
                args={"request": attempt_message},
                tool_context=tool_context,
            )
        except ValidationError as exc:
            last_error = exc
            attempt_message = (
                f"{message}\n\n"
                "IMPORTANT: Your previous response was not valid JSON "
                "matching the required schema. Respond again with ONLY a "
                "single valid JSON object matching the schema. No "
                "natural-language text, no markdown, no code fences, no "
                "mixed languages or scripts."
            )
            continue
        except ClientError as exc:
            is_quota_error = getattr(exc, "code", None) == 429
            if is_quota_error and quota_retries_left > 0:
                quota_retries_left -= 1
                delay = _extract_retry_delay_seconds(exc, default=15.0)
                await asyncio.sleep(delay)
                continue
            if is_quota_error:
                raise RuntimeError(
                    "hotel_search_quota_exhausted: The model's API quota "
                    "was exceeded and retries were unsuccessful. Ask the "
                    "user to wait a minute and try again, or reduce how "
                    "many pages/options are requested per search."
                ) from exc
            raise

        if isinstance(result, BaseModel):
            return result.model_dump(mode="json", exclude_unset=True)
        if isinstance(result, dict):
            return result
        if isinstance(result, str) and result.strip():
            return result

        last_error = ValueError(
            f"Agent '{agent.name}' returned no usable output."
        )

    raise ValueError(
        f"Agent '{agent.name}' failed to produce valid structured output "
        f"after {max_attempts} attempts."
    ) from last_error