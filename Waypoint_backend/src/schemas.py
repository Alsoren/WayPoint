"""Travel context and structured extractor output (Pydantic v2)."""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TravelContext(BaseModel):
    """Known travel details; missing information remains None."""

    model_config = ConfigDict(extra="ignore")

    origin: str | None = Field(
        default=None,
        description="Departure city. Do not store an airport code here.",
    )

    destination: str | None = Field(
        default=None,
        description="Destination city. Do not store an airport code here.",
    )

    departure_date: Date | None = Field(
        default=None,
        description="Flight departure date in YYYY-MM-DD format.",
    )

    return_date: Date | None = Field(
        default=None,
        description="Flight return date in YYYY-MM-DD format.",
    )

    check_in_date: Date | None = Field(
        default=None,
        description="Hotel check-in date in YYYY-MM-DD format.",
    )

    check_out_date: Date | None = Field(
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

    preferred_origin_airport: str | None = Field(
        default=None,
        description=(
            "Preferred departure airport explicitly stated by the user, "
            "for cities with multiple airports (e.g. SAW vs IST)."
        ),
    )
    preferred_destination_airport: str | None = Field(
        default=None,
        description=(
            "Preferred arrival airport for the destination city explicitly stated "
            "by the user, such as SAW or IST."
        ),
    )

    preferred_hotel_area: str | None = Field(
        default=None,
        description="Preferred hotel neighborhood or area, such as Çankaya.",
    )

    min_star_rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Minimum hotel star rating requested by the user.",
    )

    preferred_departure_period: Literal[
        "morning",
        "afternoon",
        "evening",
        "night",
    ] | None = Field(
        default=None,
        description="Preferred time period for the outbound flight.",
    )

    preferred_return_period: Literal[
        "morning",
        "afternoon",
        "evening",
        "night",
    ] | None = Field(
        default=None,
        description="Preferred time period for the return flight.",
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
    "preferred_origin_airport",
    "preferred_destination_airport",
    "preferred_hotel_area",
    "min_star_rating",
    "preferred_departure_period",
    "preferred_return_period"

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

    origin_airport: str
    destination_airport: str

    departure_time: str
    arrival_time: str

    duration_minutes: int | None = None

    price: float
    currency: str = "TRY"

    stops: int = 0

    booking_url: str | None = None
    cabin_class: str | None = None
    baggage: str | None = None


class FlightSearchResult(BaseModel):
    options: list[FlightOption] = Field(default_factory=list)
    search_summary: str
    source: str | None = None


class HotelOption(BaseModel):
    hotel_id: str | None = None

    name: str
    location: str | None = None

    rating: float | None = None
    hotel_star: int | None = None

    nightly_price: float | None = None
    total_price: float | None = None
    currency: str = "TRY"

    amenities: list[str] = Field(default_factory=list)

    phone: str | None = None
    property_description: str | None = None
    rooms_description: str | None = None

    policies: list[str] = Field(default_factory=list)
    faq: list[str] = Field(default_factory=list)

class HotelSearchResult(BaseModel):
    options: list[HotelOption] = Field(default_factory=list)
    search_summary: str
    source: str | None = None


class PlaceOption(BaseModel):
    name: str
    category: str | None = None
    location: str | None = None
    description: str | None = None

    estimated_visit_minutes: int | None = None

    price: float | None = None
    currency: str = "TRY"

    opening_hours: str | None = None
    phone: str | None = None
    website: str | None = None
    rating: float | None = None

    place_id: str | None = None
    maps_url: str | None = None

class WeatherSummary(BaseModel):
    available: bool = False

    date: str | None = Field(
        default=None,
        description="Weather date in YYYY-MM-DD format.",
    )

    temperature: str | None = None
    min_temperature: str | None = None
    max_temperature: str | None = None

    conditions: str | None = None
    precipitation_probability: float | None = None
    wind: str | None = None

    summary: str | None = None

class RouteSummary(BaseModel):
    origin: str
    destination: str

    travel_mode: str | None = None

    distance_meters: int | None = None
    distance_text: str | None = None

    duration_seconds: int | None = None
    duration_text: str | None = None

    route_summary: str | None = None

class SightseeingSearchResult(BaseModel):
    request_type: Literal[
        "place_discovery",
        "place_details",
        "weather",
        "route",
    ]

    destination: str | None = None

    places: list[PlaceOption] = Field(default_factory=list)

    weather: WeatherSummary | None = None

    route: RouteSummary | None = None

    search_summary: str
