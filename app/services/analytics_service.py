import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    async def get_dashboard_metrics(db: AsyncSession) -> dict:
        """
        Calculates and returns system-wide metrics including status distribution,
        category volumes, and average resolution times.
        """
        try:
            # 1. Status Distribution
            status_query = select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
            status_result = await db.execute(status_query)
            status_distribution = {status.value: count for status, count in status_result.all()}

            # 2. Category Volumes
            category_query = select(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category)
            category_result = await db.execute(category_query)
            # Handle cases where category might be None
            category_volume = {category if category else "Uncategorized": count for category, count in category_result.all()}

            # 3. Average Resolution Time (in hours)
            # Only consider tickets that have a resolved_at timestamp
            resolution_query = select(
                func.avg(
                    extract('epoch', Ticket.resolved_at) - extract('epoch', Ticket.created_at)
                )
            ).where(Ticket.resolved_at.is_not(None))
            
            resolution_result = await db.execute(resolution_query)
            avg_seconds = resolution_result.scalar_one_or_none()
            
            avg_resolution_hours = round(avg_seconds / 3600, 2) if avg_seconds else 0.0

            return {
                "status_distribution": status_distribution,
                "category_volume": category_volume,
                "average_resolution_hours": avg_resolution_hours
            }
        except Exception as e:
            logger.error(f"Failed to aggregate analytics metrics: {e}")
            raise
