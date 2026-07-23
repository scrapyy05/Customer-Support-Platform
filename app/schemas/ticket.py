import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.user import UserRead


class TicketBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Brief summary of the issue")
    description: str = Field(..., min_length=10, description="Detailed explanation of the support request")
    category: str = Field(default="General", max_length=100, description="Classification category")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="Urgency of the ticket")


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[str] = Field(None, max_length=100)
    assigned_agent_id: Optional[uuid.UUID] = None


class TicketHistoryRead(BaseModel):
    id: uuid.UUID
    old_status: str
    new_status: str
    changed_by: Optional[uuid.UUID]
    changed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TicketRead(TicketBase):
    id: uuid.UUID
    customer_id: uuid.UUID
    assigned_agent_id: Optional[uuid.UUID]
    status: TicketStatus
    ai_summary: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    history_logs: Optional[List[TicketHistoryRead]] = []

    model_config = ConfigDict(from_attributes=True)
