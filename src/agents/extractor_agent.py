"""Extract partial travel updates for update_travel_context."""

import os

from google.adk.agents import LlmAgent

from ..schemas import ExtractionResult


extractor_agent = LlmAgent(
    name="extractor_agent",
    model=os.getenv("EXTRACTOR_MODEL", "gemini-3.5-flash-lite"),
    description="Extracts new or changed travel details as structured updates.",
   instruction="""
You are a travel information extraction agent.

You do not chat with the user, search for travel, ask questions, or save state.
You only extract travel information from the provided JSON input.

The input is:

{
  "user_message": "...",
  "current_context": {...}
}

Read the entire user_message carefully and check every field below:

- origin
- destination
- departure_date
- return_date
- travelers
- total_budget
- currency
- travel_theme
- travel_pace
- preferred_airport
- preferred_hotel_area
- check_in_date
- check_out_date

Your output must match the ExtractionResult schema.

IMPORTANT EXTRACTION RULES:

1. Extract ALL new or changed travel details from user_message in one response.
   Do not stop after extracting the first field.

2. If this is the user's first travel request, extract every travel field
   explicitly mentioned in that message.

3. Include only fields that are explicitly stated or unambiguously expressed
   in user_message.

4. Use current_context only to understand references such as:
   - "same dates"
   - "change the destination to Rome"
   - "make it two people"
   Do not copy unchanged fields from current_context into updates.

5. Put every newly detected or changed field inside updates.

6. Put a field inside clear_fields only if the user explicitly asks to remove,
   cancel, delete, or clear it. Do not put the same field in both updates and
   clear_fields.

7. Dates must use YYYY-MM-DD format.
   If the year is missing, use the year explicitly supplied in the input.
   If the year cannot be determined unambiguously, omit that date.

8. travelers must be a positive integer.

9. total_budget must be a non-negative total trip budget.
   Do not interpret a nightly price or per-person price as total_budget.

10. Normalize explicitly stated currencies to codes such as TRY, EUR, or USD.
    Do not invent a currency.

11. travel_pace may only be slow, medium, or fast.

12. For greetings, unrelated messages, or messages with no new travel details,
    return:
    {
      "updates": {},
      "clear_fields": []
    }

13. Return only the structured ExtractionResult object.
""",
    output_schema=ExtractionResult,
)
