"""Call an agent from a Python tool and return its output."""

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from pydantic import BaseModel


async def run_agent(
    agent: LlmAgent,
    message: str,
    tool_context: ToolContext,
) -> dict[str, Any] | str:
    """Run an agent without input_schema using the active tool context.

    AgentTool may propagate child state changes to the caller. Keep the
    extractor free of state-writing tools, callbacks and output_key; its
    caller is responsible for merging the extracted travel updates.
    """
    if agent.input_schema is not None:
        raise ValueError("run_agent expects an agent without input_schema.")

    agent_tool = AgentTool(agent=agent)
    result = await agent_tool.run_async(
        args={"request": message},
        tool_context=tool_context,
    )

    if isinstance(result, BaseModel):
        return result.model_dump(mode="json", exclude_unset=True)
    if isinstance(result, dict):
        return result
    if isinstance(result, str) and result.strip():
        return result

    raise ValueError(f"Agent '{agent.name}' returned no usable output.")
