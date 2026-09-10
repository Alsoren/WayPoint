from google.adk.agents import LlmAgent

from ..schemas import FlightSearchResult


flight_agent = LlmAgent(
    name="flight_agent",
    model="gemini-3.5-flash-lite",
    description="Searches and compares flight options for the requested trip.",
    instruction="""
You are the flight specialist. Use the available flight search tools when provided.
Search according to the travel context in the user message. Return only factual,
structured flight results. If no option is found, return an empty options list and
explain why in search_summary. Do not invent prices or schedules.
""",
    output_schema=FlightSearchResult,
)
