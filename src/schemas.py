"""Travel context and structured extractor output (Pydantic v2)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TravelContext(BaseModel):
    """Known travel details; missing information remains None."""

    model_config = ConfigDict(extra="ignore")

    origin: str | None = Field(
        default=None,
        description="Departure city or airport.",
    )

    destination: str | None = Field(
        default=None,
        description="Main destination city.",
    )

    departure_date: date | None = Field(
        default=None,
        description="Flight departure date in YYYY-MM-DD format.",
    )

    return_date: date | None = Field(
        default=None,
        description="Flight return date in YYYY-MM-DD format.",
    )

    check_in_date: date | None = Field(
        default=None,
        description="Hotel check-in date in YYYY-MM-DD format.",
    )

    check_out_date: date | None = Field(
        default=None,
        description="Hotel check-out date in YYYY-MM-DD format.",
    )

    travelers: int | None = Field(
        default=None,
        ge=1,
        description="Number of travelers or hotel guests.",
    )

    total_budget: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description="Total trip budget, not nightly or per-person budget.",
    )

    currency: str | None = Field(
        default=None,
        description="Currency code such as TRY, EUR, or USD.",
    )

    travel_theme: str | None = Field(
        default=None,
        description="Travel theme such as culture, beach, business, or nature.",
    )

    travel_pace: Literal["slow", "medium", "fast"] | None = Field(
        default=None,
        description="Preferred travel pace: slow, medium, or fast.",
    )

    preferred_airport: str | None = Field(
        default=None,
        description="Preferred airport explicitly stated by the user.",
    )

    preferred_hotel_area: str | None = Field(
        default=None,
        description="Preferred hotel neighborhood or area, such as Çankaya.",
    )


TravelField = Literal[
    "origin",
    "destination",
    "departure_date",
    "return_date",
    "check_in_date",
    "check_out_date",
    "travelers",
    "total_budget",
    "currency",
    "travel_theme",
    "travel_pace",
    "preferred_airport",
    "preferred_hotel_area",
]


class ExtractionResult(BaseModel):
    """Updates from this message and fields explicitly requested for removal."""

    model_config = ConfigDict(extra="ignore")

    updates: TravelContext = Field(
        default_factory=TravelContext,
        description=(
            "Only travel details that are explicitly provided or changed "
            "in the latest user message. Do not copy unchanged context."
        ),
    )

    clear_fields: list[TravelField] = Field(
        default_factory=list,
        description=(
            "Fields the user explicitly asks to remove, cancel, or clear. "
            "Removal takes priority over updates."
        ),
    )


class FlightOption(BaseModel):
    airline: str
    flight_number: str | None = None
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    price: float
    currency: str = "TRY"
    stops: int = 0


class FlightSearchResult(BaseModel):
    options: list[FlightOption] = Field(default_factory=list)
    search_summary: str
    source: str | None = None


class HotelOption(BaseModel):
    name: str
    location: str
    rating: float | None = None
    nightly_price: float
    total_price: float | None = None
    currency: str = "TRY"
    amenities: list[str] = Field(default_factory=list)


class HotelSearchResult(BaseModel):
    options: list[HotelOption] = Field(default_factory=list)
    search_summary: str
    source: str | None = None


class PlaceOption(BaseModel):
    name: str
    category: str
    location: str
    description: str
    estimated_visit_minutes: int | None = None
    price: float | None = None
    currency: str = "TRY"

class WeatherSummary(BaseModel):
    available: bool = False
    summary: str | None = None
    temperature: str | None = None
    conditions: str | None = None
    recommendation: str | None = None

class SightseeingSearchResult(BaseModel):
    destination: str
    places: list[PlaceOption] = Field(default_factory=list)
    weather: WeatherSummary | None = None
    search_summary: str
