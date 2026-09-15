"""Extract partial travel updates for update_travel_context."""

from datetime import date

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..schemas import ExtractionResult
from ..config import MODEL


def _build_instruction(context: ReadonlyContext) -> str:
    # Injected fresh on every call so the model always knows the real
    # current date — without this, "18 Ağustos" with no year defaults
    # to the current year even when that date has already passed,
    # silently producing a travel date in the past (confirmed bug: a
    # session set departure_date=2026-08-18 while "today" was
    # 2026-09-13, and downstream tools then returned nonsensical or
    # mismatched data for an already-past date without ever flagging
    # it to the user).
    today = date.today().isoformat()
    return f"""
You are a travel information extraction agent.

Today's date is {today}. Use this as your reference point for
resolving any relative or year-less date the user gives you.

You do not chat with the user, search for travel, ask questions, or save state.
You only extract travel information from the provided JSON input.

The input is:

{{
  "user_message": "...",
  "current_context": {{...}}
}}

Read the entire user_message carefully and check every field below
(matches TravelContext exactly):

- origin
- destination
- departure_date
- return_date
- check_in_date
- check_out_date
- travelers
- total_budget
- currency
- travel_theme
- travel_pace
- preferred_origin_airport
- preferred_return_airport
- preferred_hotel_area
- min_star_rating

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
   - If the user gives an explicit year, use it as stated.
   - If the user gives only a month/day (e.g. "18 Ağustos", "March 5"),
     resolve it relative to today's date above: use the NEXT occurrence
     of that date. If that month/day has already passed this year
     relative to today, use next year instead of the current year.
     Example: if today is {today} and the user says "18 Ağustos" with
     no year, and August 18 of the current year has already passed,
     the correct output year is next year — never a date before today.
   - A departure_date, check_in_date, or any other travel date must
     never be set to a date before today. If you cannot resolve an
     unambiguous future date, omit that date rather than guessing one
     in the past.

8. travelers must be a positive integer.

9. total_budget must be a non-negative total trip budget.
   Do not interpret a nightly price or per-person price as total_budget.

10. Normalize explicitly stated currencies to codes such as TRY, EUR, or USD.
    Do not invent a currency.

11. travel_pace may only be slow, medium, or fast.

12. preferred_origin_airport / preferred_return_airport:
    - These are airports, not cities — only set them when the user names a
      specific airport or unambiguous airport code (e.g. "SAW", "Sabiha
      Gökçen", "IST", "Atatürk Havalimanı"), not just the destination city.
    - preferred_origin_airport is where the user wants to DEPART from
      (outbound flight).
    - preferred_return_airport is where the user wants to ARRIVE on the
      way back (return/inbound flight) — only relevant for round trips,
      and only when it may differ from the origin airport (e.g. open-jaw
      trips, or a city served by multiple airports).
    - If the user states a single preferred airport without distinguishing
      outbound vs. return (e.g. "Sabiha Gökçen'den uçmak istiyorum" with no
      trip structure implying otherwise), set preferred_origin_airport only.
      Do not guess a value for preferred_return_airport.
    - If the user says both flights should use the same airport (e.g. "hep
      Sabiha Gökçen olsun"), set both fields to that airport.

13. For greetings, unrelated messages, or messages with no new travel details,
    return:
    {{
      "updates": {{}},
      "clear_fields": []
    }}

14. Return only the structured ExtractionResult object.

15. min_star_rating:
    - Extract only when the user explicitly states a hotel star requirement.
    - Use an integer from 1 to 5.
    - Examples:
      "at least 4 stars" -> 4
      "5-star hotel" -> 5
      "3 stars or higher" -> 3
    - Do not infer a star rating from words such as "nice", "good", or "cheap".
"""


extractor_agent = LlmAgent(
    name="extractor_agent",
    model=MODEL,
    description="Extracts new or changed travel details as structured updates.",
    instruction=_build_instruction,
    output_schema=ExtractionResult,
)