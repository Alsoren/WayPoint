# WayPoint

**WayPoint** is an AI-powered multi-agent travel planning assistant that helps users search for flights, hotels, places to visit, weather information, and routes through a conversational interface.

The project is built around a supervisor-agent architecture using **Google ADK**, where specialized agents handle different travel-related tasks while sharing a common travel context.

---

## Overview

Instead of relying on a single language model to handle every request, WayPoint separates responsibilities across specialized agents.

The supervisor understands the user's request, maintains travel context, and delegates searches to the appropriate specialist.

```text
User
  |
  v
React Frontend
  |
  v
FastAPI Backend
  |
  v
Travel Supervisor
  |
  +-------------------+-------------------+
  |                   |                   |
  v                   v                   v
Flight Agent       Hotel Agent      Sightseeing Agent
  |                   |                   |
  v                   v                   v
SerpAPI MCP         Vio MCP        Google Maps MCP
                                      |
                         +------------+------------+
                         |            |            |
                       Places       Weather      Routes
```

Multiple specialist searches can be executed concurrently when the user requests more than one travel service.

---

## Features

- Conversational travel planning
- Multi-agent architecture
- Persistent travel context during an active session
- Flight search
- Hotel search and filtering
- Specific hotel information lookup
- Place and attraction discovery
- Weather lookup
- Route, distance, and travel-time queries
- Structured responses using Pydantic schemas
- Parallel specialist-agent execution
- React-based user interface
- FastAPI backend
- Dockerized frontend and backend
- Docker Compose support
- Google Cloud Run deployment

---

## Multi-Agent Architecture

### Travel Supervisor

The supervisor is the main agent communicating with the user.

Its responsibilities include:

- Understanding the current request
- Updating travel information
- Detecting missing information
- Routing requests to specialist agents
- Coordinating multiple searches
- Presenting verified results to the user

The supervisor does not directly perform external travel searches.

### Flight Agent

Responsible for:

- Searching flights
- Comparing available flight options
- Handling origin and destination airports
- Processing outbound and return flight information

Flight data is retrieved through **SerpAPI MCP**.

### Hotel Agent

Responsible for:

- Hotel discovery
- Budget filtering
- Star-rating filtering
- Hotel availability searches
- Retrieving information about specific hotels

Hotel data is retrieved through **Vio MCP**.

### Sightseeing Agent

Responsible for:

- Place discovery
- Specific place information
- Weather information
- Routes
- Distances
- Travel times

These capabilities are provided through **Google Maps MCP**.

---

## Travel Context

WayPoint maintains a structured travel context containing information such as:

```text
origin
destination
departure_date
return_date
check_in_date
check_out_date
travelers
total_budget
currency
travel_theme
travel_pace
preferred_origin_airport
preferred_destination_airport
preferred_hotel_area
min_star_rating
```

When the user provides new information, only the changed fields are extracted and merged into the existing context.

For example:

```text
User:
"I want to travel from Ankara to Istanbul."

Context:
origin = Ankara
destination = Istanbul
```

Later:

```text
User:
"We are two people."

Updated Context:
origin = Ankara
destination = Istanbul
travelers = 2
```

This allows WayPoint to support multi-turn travel planning without requiring the user to repeat previously supplied information.

---

## Technology Stack

### Backend

- Python
- FastAPI
- Google Agent Development Kit (ADK)
- Gemini
- Pydantic
- MCP
- Uvicorn
- uv

### Frontend

- React
- Vite
- JavaScript
- CSS
- Nginx

### External Services

- SerpAPI MCP
- Vio Hotel MCP
- Google Maps MCP

### Infrastructure

- Docker
- Docker Compose
- Google Cloud Run
- Google Cloud Build
- Google Artifact Registry

---

## Project Structure

```text
WayPoint/
│
├── Waypoint_backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── supervisor_agent.py
│   │   │   ├── extractor_agent.py
│   │   │   ├── flight_agent.py
│   │   │   ├── hotel_agent.py
│   │   │   └── sightseeing_agent.py
│   │   │
│   │   ├── mcp_tools/
│   │   ├── tools/
│   │   ├── agent.py
│   │   ├── agent_runner.py
│   │   ├── config.py
│   │   └── schemas.py
│   │
│   ├── api_server.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
│
├── Waypoint-frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml
└── README.md
```

---

## Running the Project with Docker

### Requirements

Make sure the following are installed:

- Docker
- Docker Compose

Clone the repository:

```bash
git clone https://github.com/Alsoren/WayPoint.git
cd WayPoint
```

Create the backend environment file:

```text
Waypoint_backend/.env
```

Example:

```env
GEMINI_API_KEY=
SERPAPI_API_KEY=
GOOGLE_MAPS_DEMO_KEY=
GOOGLE_CLOUD_PROJECT=
```

Do not commit real API keys to Git.

Build and start the complete application:

```bash
docker compose up --build
```

The services will be available at:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
```

Backend health check:

```text
http://localhost:8000/api/chat/health
```

To stop the application:

```bash
docker compose down
```

---

## Running the Backend Without Docker

Move into the backend directory:

```bash
cd Waypoint_backend
```

Install dependencies:

```bash
uv sync
```

Start the FastAPI server:

```bash
uvicorn api_server:app --reload --port 8000
```

The backend will run at:

```text
http://localhost:8000
```

---

## Running the Frontend Without Docker

Move into the frontend directory:

```bash
cd Waypoint-frontend
```

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

During development, Vite proxies `/api` requests to the FastAPI backend running on port `8000`.

---

## API

### Health Check

```http
GET /api/chat/health
```

Example response:

```json
{
  "status": "UP"
}
```

### Chat

```http
POST /api/chat
```

Example request:

```json
{
  "message": "Find me a hotel in Ankara for two people.",
  "sessionId": "example-session"
}
```

The backend forwards the request to the travel supervisor, which determines whether travel context must be updated or a specialist search must be executed.

---

## Docker Architecture

The production-style local environment consists of two containers:

```text
Browser
   |
   v
Frontend Container
React + Nginx
   |
   | /api/*
   v
Backend Container
FastAPI + Google ADK
   |
   v
External MCP Services
```

Nginx serves the frontend application and forwards API requests to the backend.

---

## Deployment

WayPoint is containerized and designed to run on **Google Cloud Run**.

The deployment pipeline uses:

```text
Source Code
    |
    v
Google Cloud Build
    |
    v
Artifact Registry
    |
    v
Cloud Run
```

The frontend and backend are deployed as separate Cloud Run services.

This allows both services to be independently updated while keeping their Cloud Run service URLs stable across revisions.

---

## Current Limitations

### In-Memory Sessions

The current FastAPI implementation uses an in-memory ADK session service.

This means travel context survives multiple requests while the same backend instance is running, but session data may be lost when:

- the container restarts
- a new Cloud Run revision is created
- the instance is terminated
- the service scales down

A persistent database-backed session system is planned for a future version.

### External Service Dependency

Flight, hotel, weather, route, and place information depend on external MCP services and their availability, quotas, and response formats.

---

## Future Improvements

Planned improvements include:

- Persistent session storage
- User authentication
- Saved trips
- Conversation history
- Improved itinerary generation
- More advanced flight filtering
- Hotel comparison
- Interactive maps
- Booking links
- Automated testing
- Observability and monitoring
- CI/CD pipeline

---

## Security

API keys and credentials must never be committed to the repository.

Environment files are excluded through `.gitignore`.

Use:

```text
.env.example
```

to document required environment variables without exposing credentials.

---

## Repository

GitHub:

https://github.com/Alsoren/WayPoint

---

## Author

Developed as an experimental multi-agent travel planning system combining LLM-based orchestration, structured tools, MCP integrations, and cloud-native deployment.
