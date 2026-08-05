import asyncio
import uuid
import logging
from sqlalchemy import select

from app.worker.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.ticket import Ticket, TicketPriority
from app.services.ai_service import AIService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

async def _categorize_ticket_async(ticket_id: str):
    """
    Async implementation of the categorization logic.
    """
    try:
        async with AsyncSessionLocal() as db:
            # 1. Fetch the ticket
            ticket_uuid = uuid.UUID(ticket_id)
            query = select(Ticket).where(Ticket.id == ticket_uuid)
            result = await db.execute(query)
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found for categorization.")
                return

            # 2. Call AI Service
            ai_result = await AIService.categorize_ticket(ticket.title, ticket.description)
            
            # 3. Update the ticket
            ticket.category = ai_result.get("category", ticket.category)
            
            # Map string to enum safely
            try:
                priority_val = ai_result.get("priority", ticket.priority.value)
                ticket.priority = TicketPriority(priority_val)
            except ValueError:
                pass # Keep original priority if AI hallucinated an invalid one
            
            ticket.ai_summary = f"Categorized automatically by AI as {ticket.category} with {ticket.priority.value} priority."
            
            await db.commit()
            
            # 4. Invalidate cache so users see the updated category/priority
            await CacheService.delete_cache(f"ticket:{ticket_id}")
            
            logger.info(f"Successfully categorized ticket {ticket_id}")
            
    except Exception as e:
        logger.error(f"Error categorizing ticket {ticket_id}: {str(e)}")


@celery_app.task(name="categorize_ticket")
def task_categorize_ticket(ticket_id: str):
    """
    Synchronous Celery task that wraps the async database and AI operations.
    """
    asyncio.run(_categorize_ticket_async(ticket_id))
    return f"Processed ticket {ticket_id}"
