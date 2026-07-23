import uuid
from fastapi import APIRouter, Depends, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.message import AttachmentRead
from app.services.message_service import MessageService
from app.auth.permissions import get_current_user

router = APIRouter()


@router.post(
    "/{id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an attachment to a message",
)
async def upload_attachment(
    id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts a multipart/form-data file upload and attaches it to a specific message.
    Only the message sender can upload attachments to their message.
    Validates file size (max 5MB) and type.
    """
    return await MessageService.upload_attachment(
        db=db, message_id=id, uploader=current_user, file=file
    )
