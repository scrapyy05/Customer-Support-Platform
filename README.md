# AI Customer Support Platform Backend

A Python FastAPI backend service that powers a next-generation customer support ticketing system. Built with a focus on high concurrency, real-time communication, and autonomous intelligence, the platform seamlessly integrates Large Language Models (LLMs) with robust enterprise engineering practices.

This project was developed to address common challenges in modern support desks: slow response times, manual ticket triaging, and complex real-time state synchronization. By pairing Google Gemini 1.5 Pro (via Celery background workers) with deterministic SQLAlchemy ORM endpoints, Redis Pub/Sub WebSockets, and stateless JWT authentication, the application provides a highly performant and intelligent support API.

---

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-316192?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0%2B-DC382D?style=flat-square&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.0%2B-37814A?style=flat-square)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-D71F00?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-1.5%20Pro-8E75B2?style=flat-square&logo=google&logoColor=white)

---

## Key Highlights

- 🚀 **Asynchronous REST APIs** built with FastAPI
- 🤖 **Auto-Categorization & AI Drafting** using Google Gemini
- ⚡ **Real-Time WebSockets** backed by Redis Pub/Sub
- 🔒 **Stateless JWT Authentication** + strict RBAC
- 📊 **PostgreSQL** + Async SQLAlchemy 2.0 ORM
- 🛡️ **Soft-Deletion Security** on all database records
- 🔄 **Decoupled AI Inference** via Celery Workers
- 📈 **Pre-compiled SQL Analytics** for Admin Dashboards

---

## Features

- **Decoupled AI Engine**: Intelligent background processing using Celery. Incoming tickets are instantly acknowledged to the user (sub-50ms), while Celery securely talks to Google Gemini in the background for auto-categorization.
- **Real-Time Chat (WebSockets)**: Bidirectional, live messaging. Messages are saved to PostgreSQL and instantly broadcast across the cluster via Redis Pub/Sub channels to eliminate manual browser refreshing.
- **Stateless JWT Authentication**: High-speed API security using Bearer tokens and password hashing via `bcrypt`. Requires zero database session lookups to validate requests.
- **RBAC & Internal Notes**: Role-Based Access Control enforcing protected routes (`Customer`, `Agent`, `Admin`). Agents can leave "Internal" notes on tickets that the API actively filters out before serving to Customers.
- **PostgreSQL & Soft Deletion**: Relational database schema handling users, tickets, and messages. Records are never dropped (`DELETE`); instead, status flags (`is_active`, `CLOSED`) ensure perfect historical audit trails.
- **Ticket Audit History**: Every state change (e.g., OPEN -> RESOLVED) automatically triggers a database hook logging the exact transition into a dedicated `TicketHistory` table.
- **Business Analytics APIs**: High-speed, pre-compiled SQL aggregation endpoints for Admin dashboards calculating ticket volumes, category distributions, and resolution times.

---

## Tech Stack

- **Backend Framework**: Python 3.10+, FastAPI, Uvicorn
- **Database & ORM**: PostgreSQL, SQLAlchemy 2.0 (Async), Alembic
- **Caching & Pub/Sub**: Redis, `redis.asyncio`
- **Background Tasks**: Celery
- **AI Integration**: Google Generative AI (`google-genai` / Gemini 1.5 Pro)
- **Authentication & Security**: Pydantic v2, `PyJWT`, `passlib[bcrypt]`

---

## Project Structure

```text
ai-support-platform/
├── app/
│   ├── api/                      # FastAPI routers
│   │   ├── ai.py                 # Endpoints to trigger AI drafting 
│   │   ├── analytics.py          # Pre-compiled Admin analytics dashboard
│   │   ├── auth.py               # User registration and JWT login
│   │   ├── messages.py           # Chat messaging and attachment uploads
│   │   ├── tickets.py            # Core ticket CRUD and state machines
│   │   └── websockets.py         # Redis Pub/Sub WebSocket handlers
│   ├── auth/                     # JWT decoding & RBAC dependencies
│   ├── core/                     # App configuration & DB/Redis singletons
│   ├── models/                   # SQLAlchemy tables (User, Ticket, Message, History)
│   ├── schemas/                  # Pydantic v2 validation schemas
│   ├── services/                 # Core business logic & database abstractions
│   └── worker/                   # Celery application & Google Gemini tasks
├── alembic/                      # Database migration scripts
├── uploads/                      # Secure file attachment storage
├── requirements.txt              # Project dependencies
└── main.py                       # ASGI application entry point
```

---

## Architecture

The application follows a decoupled, asynchronous micro-architecture to ensure that heavy LLM inference calls never block the critical request path.

```mermaid
flowchart TB
    subgraph Client ["Client Layer"]
        UI["Web App / API Client"]
        WS["WebSocket Client"]
    end

    subgraph Security ["Security Layer"]
        JWT["Stateless JWT Bearer Auth"]
        RBAC["Role-Based Access Control"]
    end

    subgraph Core ["FastAPI Application Engine"]
        CRUD["Ticket & Auth APIs<br>(REST)"]
        WSR["WebSocket Router<br>(ws://...)"]
        KPI["Analytics Endpoints<br>(GET /analytics/*)"]
    end

    subgraph AsyncData ["Asynchronous Data Layer"]
        REDIS["⚡ Redis<br>(Pub/Sub & Cache)"]
        CELERY["Celery Worker Queue"]
    end
    
    subgraph Intelligence ["AI Layer"]
        GEMINI["Google Gemini 1.5 Pro"]
    end

    subgraph Storage ["Database Layer"]
        PG[(PostgreSQL Database)]
    end

    UI --> Security
    Security --> CRUD & KPI
    WS <--> WSR
    
    CRUD --> PG
    KPI --> PG
    
    CRUD -- "Publish Message Event" --> REDIS
    WSR -- "Subscribe to Ticket ID" --> REDIS
    
    CRUD -- "Enqueue Ticket" --> CELERY
    CELERY <--> GEMINI
    CELERY -- "Auto-Categorize" --> PG
```

---

## Engineering Challenges Solved

### 1. High Inference Latency & API Blocking
Relying on LLM generation for ticket categorization synchronously blocks the ASGI event loop. An AI request can take 3-5 seconds, meaning the customer's browser hangs while waiting to create a ticket.
- **Solution**: Decoupled the AI via **Celery**. The FastAPI endpoint writes the ticket to PostgreSQL and instantly returns a `201 Created` to the user in ~30ms. It fires a `task_categorize_ticket.delay()` event. The Celery worker picks it up, talks to Gemini, and updates the database asynchronously.

### 2. Stateless Real-Time State Synchronization
Customers and Agents need to see messages instantly without refreshing, but scaling traditional HTTP polling destroys database performance.
- **Solution**: Integrated **WebSockets with Redis Pub/Sub**. When an agent posts a message via REST, the API saves it to the DB and instantly publishes the JSON payload to a Redis channel (`ticket_updates:{ticket_id}`). Active WebSockets simply subscribe to this channel and push updates to the UI in milliseconds.

### 3. Data Integrity vs. Auditing Requirements
Support platforms require perfect historical records. If an angry agent deletes a user or a ticket, the company loses vital audit data.
- **Solution**: Implemented a **Soft-Deletion Architecture**. No standard `DELETE` SQL commands are ever executed against core tables. Instead, tickets are marked `CLOSED` and users are marked `is_active = False`. Furthermore, every state change triggers an automatic log in the `TicketHistory` table.

### 4. High-Performance Dashboard Aggregations
Calculating average resolution times and category volumes by pulling thousands of rows into Python memory causes severe memory spikes.
- **Solution**: Moved all analytical math to the **Database Layer**. The `/analytics/dashboard` route executes highly optimized, pre-compiled SQLAlchemy `func.avg()` and `func.count()` aggregations directly in PostgreSQL, returning instant JSON.

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- PostgreSQL server running locally or remotely
- Redis server (Required for WebSockets and Celery Broker)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ai-support-platform.git
   cd ai-support-platform
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   APP_NAME="AI Customer Support Platform"
   ENVIRONMENT="development"
   DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_support_db"
   SECRET_KEY="your-secure-jwt-secret-key"
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REDIS_URL="redis://localhost:6379/0"
   CACHE_TTL_SECONDS=3600
   GEMINI_API_KEY="your-google-gemini-api-key"
   ```

5. **Apply database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Start the Celery Worker (In a new terminal):**
   ```bash
   celery -A app.worker.celery_app worker --loglevel=info
   ```

8. **Access documentation:**
   Open `http://localhost:8000/docs` in your browser to interact with the Swagger API interface.

---

## Screenshots

*(Visual placeholders representing primary application workflows)*

### Swagger UI & API Interface
![Swagger UI](https://via.placeholder.com/800x400.png?text=Swagger+UI+Interactive+API+Docs)

### JWT Login Endpoint
![Login Endpoint](https://via.placeholder.com/800x300.png?text=Stateless+JWT+Bearer+Login)

### Live WebSocket Chat Stream
![WebSocket](https://via.placeholder.com/800x300.png?text=Live+Redis+Pub/Sub+Message+Stream)

### Admin Analytics Dashboard
![Analytics Dashboard](https://via.placeholder.com/800x400.png?text=Pre-Compiled+SQL+Analytics+Response)

---

## Usage Example

### Live WebSocket Connection (`ws /ws/ticket/{ticket_id}`)

**Client Action:** 
Agent connects to the WebSocket URL using their JWT token.

**Terminal Output (REST API creates message):**
```text
INFO: Saving new message to PostgreSQL...
INFO: Publishing message payload to Redis channel: ticket_updates:550e8400-e29b-41d4-a716-446655440000
```

**Client WebSocket Receives Instant JSON:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender_id": "agent-uuid-here",
  "content": "I have restarted your billing cycle. You should be good to go!",
  "is_internal": false,
  "is_ai": false,
  "created_at": "2026-09-02T12:00:00Z"
}
```

---

## Future Improvements

- **Email Integration**: Configure Celery to send automated email notifications (via SendGrid/AWS SES) when a ticket's status changes or a new message is received while the customer is offline.
- **Rate Limiting**: Implement SlowAPI to throttle aggressive endpoints (like file uploads and AI drafting requests) to prevent DDOS and protect Gemini API billing.
- **S3 Attachment Storage**: Migrate local file uploads (`/uploads` directory) to AWS S3 using `boto3` to ensure perfect statelessness for multi-server Kubernetes deployments.
