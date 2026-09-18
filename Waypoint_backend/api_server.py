"""WayPoint Agent API — gerçek ADK ajanına bağlı FastAPI sunucusu.

Bu dosyayı Waypoint proje kökünde (src/ klasörüyle aynı dizinde) çalıştır:

    uvicorn api_server:app --reload --port 8000

Frontend (React) http://localhost:8000/api/chat adresine POST atar.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# root_agent = supervisor_agent (src/agent.py içinde load_dotenv() zaten çağrılıyor)
from src.agent import root_agent

APP_NAME = "waypoint"

app = FastAPI(title="WayPoint Agent API")

# React arayüzünün erişebilmesi için CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ADK Runner + Session Service (uygulama ömrü boyunca tek örnek) ---
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = "default"
    currentState: Optional[Dict[str, Any]] = None  # şu an kullanılmıyor; gerçek state ADK session'ında tutuluyor


class ChatResponse(BaseModel):
    reply: str
    intent: str
    state: Dict[str, Any]
    toolCalled: Optional[str] = None
    results: List[Dict[str, Any]] = []


@app.get("/api/chat/health")
def health():
    return {"status": "UP"}


# ---------------------------------------------------------------------
# Yardımcılar: ajanın döndürdüğü Pydantic-şema sonuçlarını (FlightOption,
# HotelOption, PlaceOption) frontend'in beklediği düz kart formatına çeviriyor.
# ---------------------------------------------------------------------

def _fmt_price(amount: Optional[float], currency: str) -> Optional[str]:
    if amount is None:
        return None
    return f"{amount:,.0f} {currency}".replace(",", ".")


def _map_flight(opt: Dict[str, Any]) -> Dict[str, Any]:
    stops = opt.get("stops") or 0
    label = " ".join(
        p for p in [opt.get("airline"), opt.get("flight_number")] if p
    ).strip()
    return {
        "type": "flight",
        "name": label or "Uçuş",
        "badge": "Direkt" if stops == 0 else f"{stops} Aktarmalı",
        "price": _fmt_price(opt.get("price"), opt.get("currency", "TRY")),
        "departureTime": opt.get("departure_time"),
        "arrivalTime": opt.get("arrival_time"),
        "originAirport": opt.get("origin_airport"),
        "destinationAirport": opt.get("destination_airport"),
        "durationMinutes": opt.get("duration_minutes"),
        "bookingUrl": opt.get("booking_url"),
    }


def _map_hotel(opt: Dict[str, Any]) -> Dict[str, Any]:
    price = opt.get("total_price") if opt.get("total_price") is not None else opt.get("nightly_price")
    badge = opt.get("location") or (
        f"{opt.get('hotel_star')} Yıldız" if opt.get("hotel_star") else None
    )
    return {
        "type": "hotel",
        "name": opt.get("name"),
        "badge": badge,
        "rating": opt.get("rating"),
        "price": _fmt_price(price, opt.get("currency", "TRY")),
        "amenities": opt.get("amenities", []),
    }


def _map_place(opt: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "place",
        "name": opt.get("name"),
        "badge": opt.get("category"),
        "rating": opt.get("rating"),
        "hours": opt.get("opening_hours"),
        "price": _fmt_price(opt.get("price"), opt.get("currency", "TRY")),
    }


def _extract_search_results(tool_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """search_travel tool'unun dönüşünü (status/results) düz karta çevirir."""
    results: List[Dict[str, Any]] = []
    if not tool_response or tool_response.get("status") != "completed":
        return results

    task_results = tool_response.get("results", {})
    for task, payload in task_results.items():
        if not isinstance(payload, dict):
            continue
        if task == "flight":
            results.extend(_map_flight(o) for o in payload.get("options", []))
        elif task == "hotel":
            results.extend(_map_hotel(o) for o in payload.get("options", []))
        elif task == "sightseeing":
            results.extend(_map_place(p) for p in payload.get("places", []))
    return results


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    user_id = req.sessionId or "default"
    session_id = req.sessionId or "default"

    # Oturum yoksa oluştur (ADK session_id'yi create_session'da biz veriyoruz)
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    content = types.Content(role="user", parts=[types.Part(text=req.message)])

    final_text = ""
    tool_called: Optional[str] = None
    tool_response: Dict[str, Any] = {}
    needs_input_task: Optional[str] = None

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    fc = part.function_call
                    if fc and fc.name == "search_travel":
                        tool_called = "search_travel"

                    fr = part.function_response
                    if fr and fr.name == "search_travel":
                        tool_response = fr.response or {}
                        if tool_response.get("status") == "needs_input":
                            needs_input_task = tool_response.get("task")

            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(
                    p.text for p in event.content.parts if p.text
                )
    except RuntimeError as exc:
        # agent_runner.py kota hatalarını temiz bir RuntimeError'a çeviriyor
        return ChatResponse(
            reply=f"Üzgünüm, şu anda isteğini işleyemedim: {exc}",
            intent="error",
            state={},
            toolCalled=tool_called,
            results=[],
        )

    results = _extract_search_results(tool_response)

    if needs_input_task:
        intent = needs_input_task
    elif tool_response.get("status") == "completed":
        tasks = list(tool_response.get("results", {}).keys())
        intent = "_".join(tasks) if tasks else "general"
    else:
        intent = "general"

    # Güncel seyahat bağlamını (origin/destination/dates/...) session state'inden oku
    updated_session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    state = dict(updated_session.state.get("context", {})) if updated_session else {}

    return ChatResponse(
        reply=final_text or "Üzgünüm, bir cevap üretemedim.",
        intent=intent,
        state=state,
        toolCalled=tool_called,
        results=results,
    )