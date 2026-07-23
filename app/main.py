from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db
from app.api import auth, users, tickets, messages, websockets

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-quality AI Customer Support Platform Backend built with FastAPI, Async SQLAlchemy, Celery, and Redis.",
)

# Configure CORS Middleware for client application integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in strict production deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["User Management"])
app.include_router(tickets.router, prefix="/tickets", tags=["Ticket Management"])
app.include_router(messages.router, prefix="/messages", tags=["Messages & Attachments"])
app.include_router(websockets.router, prefix="/ws", tags=["Real-time WebSockets"])


@app.get(
    "/system-health",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Check system health and database connectivity",
)
async def system_health(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify that the application and PostgreSQL database connection are responsive.
    """
    try:
        # Execute a fast ping check query against the database
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "database": db_status,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """
    Global exception handler to ensure all unhandled server errors return a clean JSON response.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred.",
        },
    )
