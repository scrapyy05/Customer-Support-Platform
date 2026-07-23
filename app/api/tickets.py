import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.ticket import TicketStatus, TicketPriority
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate
from app.schemas.message import MessageCreate, MessageRead
from app.services.ticket_service import TicketService
from app.services.message_service import MessageService
from app.auth.permissions import get_current_user, require_roles

router = APIRouter()


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket",
)
async def create_ticket(
    ticket_in: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TicketService.create_ticket(db=db, customer=current_user, ticket_in=ticket_in)


@router.get(
    "",
    response_model=List[TicketRead],
    status_code=status.HTTP_200_OK,
    summary="List tickets with filtering",
)
async def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority_filter: Optional[TicketPriority] = Query(None, alias="priority"),
    category_filter: Optional[str] = Query(None, alias="category"),
    assigned_agent_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Customers only see their own tickets.
    Agents and Admins can see all tickets and use the filters.
    """
    return await TicketService.list_tickets(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        priority_filter=priority_filter,
        category_filter=category_filter,
        assigned_agent_id=assigned_agent_id,
    )


@router.get(
    "/{id}",
    response_model=TicketRead,
    status_code=status.HTTP_200_OK,
    summary="Get ticket details and history logs",
)
async def get_ticket(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TicketService.get_ticket_by_id(db=db, ticket_id=id, user=current_user)


@router.patch(
    "/{id}",
    response_model=TicketRead,
    status_code=status.HTTP_200_OK,
    summary="Update a ticket (Agents & Admins)",
    dependencies=[Depends(require_roles(UserRole.AGENT, UserRole.ADMIN))],
)
async def update_ticket(
    id: uuid.UUID,
    ticket_update: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update ticket status, priority, or assignment.
    Automatically logs status changes to the ticket history.
    """
    return await TicketService.update_ticket(
        db=db, ticket_id=id, user=current_user, update_data=ticket_update
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Forcibly close a ticket (Admin only)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def delete_ticket(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete operation that sets the ticket status to CLOSED.
    """
    await TicketService.delete_ticket(db=db, ticket_id=id, admin_user=current_user)


@router.post(
    "/{id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a ticket",
)
async def add_ticket_message(
    id: uuid.UUID,
    message_in: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adds a message to the conversation.
    """
    return await MessageService.add_message(db=db, ticket_id=id, sender=current_user, message_in=message_in)


@router.get(
    "/{id}/messages",
    response_model=List[MessageRead],
    status_code=status.HTTP_200_OK,
    summary="List all messages in a ticket",
)
async def list_ticket_messages(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists messages ordered by created_at.
    Internal notes are hidden from customers.
    """
    return await MessageService.list_messages(db=db, ticket_id=id, user=current_user)
