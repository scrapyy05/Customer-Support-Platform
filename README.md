# AI Customer Support Platform (Backend)

A production-grade, asynchronous backend for an AI-powered Customer Support Platform. Built with FastAPI, PostgreSQL, Redis, Celery, and Google Gemini.

## 🚀 Features

- **Asynchronous Core**: Fully async API built on FastAPI, `asyncpg`, and `redis.asyncio` for high performance.
- **Role-Based Access Control (RBAC)**: Secure multi-role architecture (Customers, Agents, Admins).
- **Stateless Authentication**: Pure JWT access tokens (no refresh tokens or DB session lookups).
- **Ticket Management**: Soft-deletion, assignment, and automated history auditing.
- **Real-time WebSockets**: Live pub/sub conversation threads using Redis.
- **Redis Caching**: Highly optimized read paths for tickets with automatic invalidation.
- **AI Intelligence**: Background Celery workers leverage Google Gemini for ticket auto-categorization and agent auto-reply generation.

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (via Async SQLAlchemy & Alembic)
- **Caching & Pub/Sub**: Redis
- **Background Tasks**: Celery
- **AI Integration**: Google Generative AI (Gemini)
- **Authentication**: JWT (PyJWT) & bcrypt

## ⚙️ Project Structure

```
ai-support-platform/
├── alembic/                # Database migration versions
├── app/
│   ├── api/                # FastAPI routers (auth, users, tickets, messages, ai, websockets)
│   ├── auth/               # JWT token generation and RBAC dependencies
│   ├── core/               # App config, database, and Redis connections
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic validation schemas
│   ├── services/           # Core business logic and database abstractions
│   └── worker/             # Celery app and background tasks
├── uploads/                # Secure ticket attachment storage
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic configuration
└── main.py                 # Application entry point
```

## 💻 Local Setup & Installation

### 1. Prerequisites
- Python 3.10+
- PostgreSQL
- Redis Server (Required for WebSockets and Celery)

### 2. Environment Variables
Create a `.env` file in the root directory (refer to `.env.example`):
```env
APP_NAME="AI Customer Support Platform"
ENVIRONMENT="development"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_support_db"
SECRET_KEY="your-super-secret-jwt-key"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL="redis://localhost:6379/0"
CACHE_TTL_SECONDS=3600
GEMINI_API_KEY="your-google-gemini-key"
GEMINI_MODEL="gemini-1.5-pro"
```

### 3. Installation
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Database Migrations
Make sure your PostgreSQL database is running and matches the `DATABASE_URL`.
```bash
alembic upgrade head
```

## 🚀 Running the Application

You will need to run the FastAPI server and the Celery worker concurrently.

**1. Start the API Server:**
```bash
uvicorn app.main:app --reload
```
*The API will be available at http://127.0.0.1:8000*
*Swagger UI Documentation is available at http://127.0.0.1:8000/docs*

**2. Start the Celery Worker (In a separate terminal):**
```bash
celery -A app.worker.celery_app worker --loglevel=info
```

## 🔒 Design Decisions & Constraints

- **Soft Deletes Only**: Tickets and Users are never permanently deleted from the database. Instead, their `status` or `is_active` flags are updated.
- **Stateless Auth**: Refresh tokens have been intentionally stripped out to maintain a purely stateless, highly scalable authentication layer.
- **Cache Isolation**: Ticket responses are cached in Redis. The `CacheService` acts as a generic wrapper, while domain-specific key generation and invalidation are managed strictly by the `TicketService`.
- **Private Internal Notes**: Agents can leave `is_internal=True` notes on tickets. The backend service layer strictly filters these out before returning payloads to users with the `Customer` role.
