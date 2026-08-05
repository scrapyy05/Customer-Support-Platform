import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.auth.permissions import get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.services.ai_service import AIService
from app.services.ticket_service import TicketService

router = APIRouter()

@router.post("/tickets/{id}/suggest-reply", response_model=dict)
async def suggest_reply_for_ticket(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes the conversation history of a ticket and generates a draft reply.
    Only available to Agents and Admins.
    """
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot use the AI assist feature."
        )

    # We use ORM directly here to get all messages easily, 
    # but we first verify they have access to the ticket (which they do as Agent/Admin).
    query = select(Ticket).options(
        selectinload(Ticket.messages)
    ).where(Ticket.id == id)
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        
    if not ticket.messages:
        return {"draft": "Hello! Thank you for reaching out. How can I assist you with this ticket today?"}
        
    # Construct history
    history_lines = []
    for msg in ticket.messages:
        sender_type = "Agent/Admin" if msg.is_ai or getattr(msg.sender, "role", "") != UserRole.CUSTOMER else "Customer"
        # Optional: handle if sender is None (deleted user)
        history_lines.append(f"{sender_type}: {msg.content}")
        
    history_str = "\n".join(history_lines)
    
    # Generate draft
    draft = await AIService.suggest_reply(history_str)
    
    return {"draft": draft}
