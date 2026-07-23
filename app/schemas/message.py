import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class AttachmentRead(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    uploaded_at: datetime
    # Note: file_path is explicitly NOT included here to secure storage internals
    
    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Text content of the message")
    is_internal: bool = Field(default=False, description="True if this is an agent-only internal note")


class MessageRead(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    is_internal: bool
    created_at: datetime
    
    attachments: List[AttachmentRead] = []

    model_config = ConfigDict(from_attributes=True)
