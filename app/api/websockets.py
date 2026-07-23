import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.auth.jwt import decode_token
from app.models.user import User, UserRole
from sqlalchemy import select
from app.services.websocket_manager import ws_manager
from app.services.ticket_service import TicketService

router = APIRouter()

async def get_user_from_token(token: str) -> User:
    """
    Helper to manually resolve a user from a JWT token in a WebSocket context
    where normal FastAPI dependencies are harder to handle cleanly on disconnects.
    """
    payload = decode_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise ValueError("Invalid token")
        
    async with async_session_maker() as db:
        query = select(User).where(User.id == uuid.UUID(user_id_str))
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("User inactive or not found")
        return user


@router.websocket("/tickets/{id}")
async def websocket_endpoint(
    websocket: WebSocket,
    id: uuid.UUID,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time ticket updates.
    Expects the JWT token in the query string: ?token=...
    """
    try:
        user = await get_user_from_token(token)
    except ValueError:
        await websocket.close(code=1008)
        return

    # Verify access to the ticket
    try:
        async with async_session_maker() as db:
            await TicketService.get_ticket_by_id(db, id, user)
    except Exception:
        await websocket.close(code=1008)
        return

    # Connect to the manager
    ticket_id_str = str(id)
    await ws_manager.connect(websocket, ticket_id_str)
    
    try:
        while True:
            # We don't expect clients to send messages here (they use the POST endpoint)
            # but we need to keep the connection open and listen for disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, ticket_id_str)
