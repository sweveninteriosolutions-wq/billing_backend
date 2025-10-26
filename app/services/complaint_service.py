# app/services/billing_services/complaint_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.complaint_models import Complaint
from app.utils.activity_helpers import log_user_activity

async def create_complaint(db: AsyncSession, complaint_data, _user):
    complaint = Complaint(**complaint_data.dict(), created_by=_user.id)
    db.add(complaint)
    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Soft-deleted complaint ID {complaint.id} by user '{_user.username}'"
    )
    await db.commit()
    await db.refresh(complaint)
    return complaint

async def get_all_complaints(db: AsyncSession):
    result = await db.execute(select(Complaint).where(Complaint.is_deleted==False))
    return result.scalars().all()

async def get_complaint_by_id(db: AsyncSession, complaint_id: int):
    result = await db.execute(select(Complaint).where(Complaint.id==complaint_id, Complaint.is_deleted==False))
    return result.scalar_one_or_none()

async def update_complaint(db: AsyncSession, complaint_id: int, data, _user):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None
    for key, value in data.dict(exclude_unset=True).items():
        setattr(complaint, key, value)
    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Updated complaint ID {complaint.id} by user '{_user.username}'"
    )
    await db.commit()
    await db.refresh(complaint)
    return complaint

async def delete_complaint(db: AsyncSession, complaint_id: int, _user):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None
    complaint.is_deleted = True
    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Soft-deleted complaint ID {complaint.id} by user '{_user.username}'"
    )
    await db.commit()
    await db.refresh(complaint, attribute_names=[
        "id", "created_at", "updated_at"
    ])

    return complaint
