import uuid
import os
import shutil
from typing import List
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.ticket import TicketStatus
from app.models.message import TicketMessage, Attachment
from app.schemas.message import MessageCreate
from app.services.ticket_service import TicketService


class MessageService:
    @staticmethod
    async def add_message(
        db: AsyncSession, ticket_id: uuid.UUID, sender: User, message_in: MessageCreate
    ) -> TicketMessage:
        """
        Adds a message to a ticket.
        """
        # Ensure user has access to the ticket
        ticket = await TicketService.get_ticket_by_id(db, ticket_id, sender)

        # Prevent messages on closed/resolved tickets
        if ticket.status in [TicketStatus.CLOSED, TicketStatus.RESOLVED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add messages to a closed or resolved ticket.",
            )

        # Reject customers trying to create internal notes
        if message_in.is_internal and sender.role == UserRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers are not allowed to create internal notes.",
            )

        new_message = TicketMessage(
            ticket_id=ticket.id,
            sender_id=sender.id,
            content=message_in.content,
            is_internal=message_in.is_internal,
        )
        db.add(new_message)
        await db.commit()
        await db.refresh(new_message)
        # Reload with attachments (empty for now)
        fetched_message = await MessageService._get_message_by_id(db, new_message.id)
        
        # Broadcast via WebSockets
        from app.services.websocket_manager import ws_manager
        from app.schemas.message import MessageRead
        
        message_dict = MessageRead.model_validate(fetched_message).model_dump(mode="json")
        await ws_manager.broadcast_to_ticket(str(ticket.id), message_dict)
        
        return fetched_message

    @staticmethod
    async def list_messages(db: AsyncSession, ticket_id: uuid.UUID, user: User) -> List[TicketMessage]:
        """
        Retrieves all messages for a ticket, ordered by created_at.
        Filters out internal notes for customers.
        """
        # Ensure access
        await TicketService.get_ticket_by_id(db, ticket_id, user)

        query = select(TicketMessage).options(selectinload(TicketMessage.attachments)).where(
            TicketMessage.ticket_id == ticket_id
        ).order_by(TicketMessage.created_at.asc())

        if user.role == UserRole.CUSTOMER:
            query = query.where(TicketMessage.is_internal == False)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def upload_attachment(
        db: AsyncSession, message_id: uuid.UUID, uploader: User, file: UploadFile
    ) -> Attachment:
        """
        Uploads a file and attaches it to a specific message.
        """
        # 1. Fetch the message
        message = await MessageService._get_message_by_id(db, message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

        # 2. Verify ownership (only the sender can attach files to their own message)
        if message.sender_id != uploader.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only attach files to your own messages.",
            )

        # 3. Validate file size (max 5MB) and type
        MAX_SIZE = 5 * 1024 * 1024
        ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf", "text/plain"]
        
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File too large. Maximum size is 5MB."
            )
            
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_TYPES)}."
            )

        # 4. Generate unique filename and store
        os.makedirs("uploads", exist_ok=True)
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        storage_path = os.path.join("uploads", unique_filename)

        try:
            with open(storage_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save file."
            )

        # 5. Create database record
        new_attachment = Attachment(
            message_id=message.id,
            filename=file.filename or unique_filename,
            file_path=storage_path,
            content_type=file.content_type,
            file_size=file_size,
        )
        db.add(new_attachment)
        await db.commit()
        await db.refresh(new_attachment)

        return new_attachment

    @staticmethod
    async def _get_message_by_id(db: AsyncSession, message_id: uuid.UUID) -> TicketMessage:
        query = select(TicketMessage).options(selectinload(TicketMessage.attachments)).where(
            TicketMessage.id == message_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
