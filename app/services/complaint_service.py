# app/services/billing_services/complaint_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.complaint_models import Complaint

async def create_complaint(db: AsyncSession, complaint_data, user_id: int):
    complaint = Complaint(**complaint_data.dict(), created_by=user_id)
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    return complaint

async def get_all_complaints(db: AsyncSession):
    result = await db.execute(select(Complaint).where(Complaint.is_deleted==False))
    return result.scalars().all()

async def get_complaint_by_id(db: AsyncSession, complaint_id: int):
    result = await db.execute(select(Complaint).where(Complaint.id==complaint_id, Complaint.is_deleted==False))
    return result.scalar_one_or_none()

async def update_complaint(db: AsyncSession, complaint_id: int, data):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None
    for key, value in data.dict(exclude_unset=True).items():
        setattr(complaint, key, value)
    await db.commit()
    await db.refresh(complaint)
    return complaint

async def delete_complaint(db: AsyncSession, complaint_id: int):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None
    complaint.is_deleted = True
    await db.commit()
    await db.refresh(complaint, attribute_names=[
        "id", "created_at", "updated_at"
    ])

    return complaint
