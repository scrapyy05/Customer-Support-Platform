import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.history import TicketHistory
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketRead
from app.services.cache_service import CacheService
from app.core.config import settings
import json


class TicketService:
    @staticmethod
    async def create_ticket(db: AsyncSession, customer: User, ticket_in: TicketCreate) -> Ticket:
        """
        Creates a new support ticket linked to the customer.
        """
        new_ticket = Ticket(
            customer_id=customer.id,
            title=ticket_in.title,
            description=ticket_in.description,
            category=ticket_in.category,
            priority=ticket_in.priority,
            status=TicketStatus.OPEN,
        )
        db.add(new_ticket)
        await db.commit()
        await db.refresh(new_ticket)
        return new_ticket

    @staticmethod
    async def list_tickets(
        db: AsyncSession,
        user: User,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[TicketStatus] = None,
        priority_filter: Optional[TicketPriority] = None,
        category_filter: Optional[str] = None,
        assigned_agent_id: Optional[uuid.UUID] = None,
    ) -> List[Ticket]:
        """
        Lists tickets. Customers only see their own. Admins/Agents can see all and apply filters.
        """
        query = select(Ticket).options(selectinload(Ticket.history_logs)).offset(skip).limit(limit)

        # Enforce Customer isolation
        if user.role == UserRole.CUSTOMER:
            query = query.where(Ticket.customer_id == user.id)
        else:
            # Agents and Admins can filter
            if assigned_agent_id:
                query = query.where(Ticket.assigned_agent_id == assigned_agent_id)

        # Common filters
        if status_filter:
            query = query.where(Ticket.status == status_filter)
        if priority_filter:
            query = query.where(Ticket.priority == priority_filter)
        if category_filter:
            query = query.where(Ticket.category == category_filter)

        # Sort by newest first
        query = query.order_by(Ticket.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def _get_ticket_orm(db: AsyncSession, ticket_id: uuid.UUID, user: User) -> Ticket:
        """
        Internal method to fetch the ORM object for updates/deletes.
        """
        query = select(Ticket).options(selectinload(Ticket.history_logs)).where(Ticket.id == ticket_id)
        result = await db.execute(query)
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

        if user.role == UserRole.CUSTOMER and ticket.customer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You can only view your own tickets."
            )

        return ticket

    @staticmethod
    async def get_ticket_by_id(db: AsyncSession, ticket_id: uuid.UUID, user: User) -> dict:
        """
        Fetches a ticket by ID, using Redis caching. Customers can only fetch their own.
        """
        cache_key = f"ticket:{ticket_id}"
        cached_data_str = await CacheService.get_cache(cache_key)
        
        if cached_data_str is not None:
            try:
                cached_data = json.loads(cached_data_str)
                # Enforce access control on cached data
                if user.role == UserRole.CUSTOMER and cached_data.get("customer_id") != str(user.id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You can only view your own tickets."
                    )
                return cached_data
            except json.JSONDecodeError:
                pass

        ticket = await TicketService._get_ticket_orm(db, ticket_id, user)
        
        # Serialize and cache
        ticket_dict = TicketRead.model_validate(ticket).model_dump(mode="json")
        await CacheService.set_cache(cache_key, json.dumps(ticket_dict), expire_seconds=settings.CACHE_TTL_SECONDS)
        
        return ticket_dict

    @staticmethod
    async def update_ticket(
        db: AsyncSession, ticket_id: uuid.UUID, user: User, update_data: TicketUpdate
    ) -> Ticket:
        """
        Updates a ticket. If the status changes, automatically logs the transition to TicketHistory.
        """
        ticket = await TicketService._get_ticket_orm(db, ticket_id, user)

        update_dict = update_data.model_dump(exclude_unset=True)

        # Handle status change logging
        if "status" in update_dict and update_dict["status"] != ticket.status:
            old_status = ticket.status.value
            new_status = update_dict["status"].value
            
            # Log the history
            history_log = TicketHistory(
                ticket_id=ticket.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=user.id,
            )
            db.add(history_log)

            # Mark resolved time if closing/resolving
            if update_dict["status"] in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                ticket.resolved_at = datetime.now(timezone.utc)
            elif ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                # Re-opening ticket
                ticket.resolved_at = None

        for field, value in update_dict.items():
            setattr(ticket, field, value)

        await db.commit()
        
        # Invalidate cache
        await CacheService.delete_cache(f"ticket:{ticket_id}")
        
        # We can't just refresh if we are going to return a cached dict
        # Wait, since the route expects a dict or model, and the route uses TicketRead, 
        # it's fine to just return the fresh dict.
        return await TicketService.get_ticket_by_id(db, ticket.id, user)

    @staticmethod
    async def delete_ticket(db: AsyncSession, ticket_id: uuid.UUID, admin_user: User) -> None:
        """
        Admin-only soft delete by closing the ticket.
        """
        if admin_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can delete/close tickets forcibly."
            )
            
        ticket = await TicketService._get_ticket_orm(db, ticket_id, admin_user)
        
        if ticket.status != TicketStatus.CLOSED:
            # Log the forced closure
            history_log = TicketHistory(
                ticket_id=ticket.id,
                old_status=ticket.status.value,
                new_status=TicketStatus.CLOSED.value,
                changed_by=admin_user.id,
            )
            db.add(history_log)
            ticket.status = TicketStatus.CLOSED
            ticket.resolved_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            # Invalidate cache
            await CacheService.delete_cache(f"ticket:{ticket_id}")
