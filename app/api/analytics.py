from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.permissions import require_roles
from app.models.user import User, UserRole
from app.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

@router.get("/dashboard", dependencies=[Depends(require_roles(UserRole.ADMIN))])
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated analytics metrics for the entire platform.
    Only accessible by ADMIN users.
    """
    try:
        metrics = await AnalyticsService.get_dashboard_metrics(db)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics metrics"
        )
