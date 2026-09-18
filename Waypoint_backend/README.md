# Waypoint

A multi-agent AI travel planner built on Google's [ADK](https://github.com/google/adk-python). A supervisor agent routes a conversation across specialist agents for hotels, flights, and sightseeing, each backed by real third-party MCP servers (Vio, SerpApi Google Flights, OpenStreetMap) rather than mocked data.

## Architecture

```
                         ┌────────────────────┐
   user message   ───►   │  supervisor_agent   │
                         └─────────┬───────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌───────────────┐┌──────────────┐┌──────────────────┐
            │  hotel_agent   ││ flight_agent ││ sightseeing_agent │
            └───────┬────────┘└──────┬───────┘└─────────┬────────┘
                    │                │                  │
                    ▼                ▼                  ▼
         search_hotels_full  search_flights_full    osm_mcp / weather_mcp
           (deterministic       (deterministic
            pagination +         pagination +
            budget filter)       token flow)
                    │                │
                    ▼                ▼
              hotel_mcp          flight_mcp
             (Vio MCP)         (SerpApi Google
                                 Flights MCP)
```

Key design decision: **multi-step orchestration (pagination, budget filtering, currency handling, de-duplication across turns) lives in plain Python wrapper tools (`search_hotels_full`, `search_flights_full`), not in LLM instructions.** Early versions asked the LLM to decide when to paginate, do its own budget arithmetic, and track which hotels it had already shown — a smaller model (`gemini-3.5-flash-lite`) turned out to be unreliable at all three. Moving that logic into deterministic code removed an entire class of intermittent bugs. See [Debugging Journey](#debugging-journey) below for the specifics.

## Setup

```bash
# create and activate a virtual environment
uv venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate    # macOS/Linux

# install dependencies
pip install -r requirements.txt

# configure environment
copy .env.example .env         # Windows
# cp .env.example .env          # macOS/Linux
# then edit .env and set GEMINI_API_KEY

# run
adk web
```

Open `http://127.0.0.1:8000` and select the `src` app.

## Project structure

```
src/
├── agent.py                    # root agent entrypoint
├── agent_runner.py             # shared sub-agent runner (retry on
│                                #   invalid JSON output and on 429
│                                #   quota errors, with backoff)
├── config.py                   # model name, shared constants
├── schemas.py                  # Pydantic output schemas
├── agents/
│   ├── supervisor_agent.py     # routes the conversation, holds
│   │                            #   travel_context across turns
│   ├── extractor_agent.py      # pulls structured trip details out
│   │                            #   of free-form user messages
│   ├── hotel_agent.py          # hotel search + detail lookups
│   ├── flight_agent.py         # flight search, round-trip token flow
│   └── sightseeing_agent.py    # points of interest
├── mcp_tools/
│   ├── hotel_mpc.py            # Vio MCP connection
│   ├── flight_mcp.py           # SerpApi Google Flights MCP connection
│   ├── osm.py                  # OpenStreetMap MCP connection
│   └── weather.py              # weather MCP connection
└── tools/
    ├── search_hotels_full.py   # deterministic multi-page hotel search
    ├── search_flights_full.py  # deterministic multi-page flight search
    ├── search_travel.py        # dispatches to the right agent(s)
    └── update_travel_context.py
```

## Debugging journey

This project went through several rounds of debugging against the *live* Vio and SerpApi MCP servers, using session traces rather than guesswork. A few of the more interesting root causes:

- **Silent budget filter failures.** Early on, searching with a tight budget (e.g. 10,000 TRY) sometimes returned zero hotels, while a looser budget on the exact same query returned hotels well under 10,000 TRY. Root cause: the wrapper read `hotel["totalPrice"]`, a field that doesn't exist — real prices live under `hotel["offers"]["cheapestRate"]["displayPrice"]`. Every price silently parsed as `None`, so the "no budget" branch (`in_budget = all_hotels`) accidentally worked while the "with budget" branch (`in_budget = []`) always failed.
- **Pagination never happened.** `search_hotels` only returns the first page (10 results) unless you explicitly follow `nextOffsets`. Every search for the same city/dates returned the exact same 10 hotels in the exact same order, regardless of budget, because nothing ever fetched page 2. Fixed by moving pagination out of the LLM's judgment and into a deterministic loop in `search_hotels_full`.
- **Currency ambiguity.** The API auto-derives currency from the caller's IP when not specified, which is not reliable for a server-side agent. Rather than manually converting the user's TRY budget into EUR with a hardcoded exchange rate (fragile, and wrong the moment rates move), the fix was to explicitly request `"currency": "TRY"` and compare budgets with zero conversion.
- **`isPartialMatch` hotels leaking into "in budget" results.** The upstream API can return hotels that don't fully match the requested filters (including price) when there aren't enough exact matches — documented behavior, not a bug on Vio's side. The wrapper now excludes `isPartialMatch: true` hotels from `hotels_in_budget` so the upstream's "best effort" hotels never get reported as strictly in-budget.
- **Structured-output failures.** With multiple tool calls layered in a single turn, the model occasionally returned malformed / mixed-script JSON instead of the required schema. `agent_runner.py` now retries once with an explicit "your last output was invalid JSON, resend as pure JSON" instruction before failing.
- **429 quota errors surfacing as raw tracebacks.** Aggressive pagination under the free-tier Gemini quota occasionally hit `RESOURCE_EXHAUSTED`. `agent_runner.py` now reads Google's suggested `retryDelay` out of the error and retries automatically before falling back to a clean, user-facing error message.

## Known limitations

- `sightseeing_agent.py` hasn't been through the same live-trace hardening as the hotel/flight agents yet.
- No automated test suite — bugs above were caught and verified against live session traces rather than unit tests.
- No frontend beyond ADK's built-in dev UI.
