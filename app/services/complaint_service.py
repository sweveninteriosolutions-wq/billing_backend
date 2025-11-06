from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime

from app.models.complaint_models import Complaint
from app.utils.activity_helpers import log_user_activity
from app.schemas.complaint_schema import ComplaintCreate, ComplaintUpdate
from app.models.user_models import User

from fastapi import HTTPException, status
from sqlalchemy import select, and_

# ➕ Create Complaint
async def create_complaint(db: AsyncSession, complaint_data: ComplaintCreate, _user: User):
    """
    Create a new complaint with validation:
    - Prevent duplicates for the same invoice_id + product_id + customer_id combo.
    """
    # ✅ Duplicate check: same customer + invoice + product
    duplicate_query = select(Complaint).where(
        and_(
            Complaint.customer_id == complaint_data.customer_id,
            Complaint.product_id == complaint_data.product_id,
            Complaint.invoice_id == complaint_data.invoice_id,
            Complaint.is_deleted == False,
        )
    )
    result = await db.execute(duplicate_query)
    existing = result.unique().scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"A complaint already exists for this product "
                f"(Product ID: {complaint_data.product_id}) under the same invoice "
                f"(Invoice ID: {complaint_data.invoice_id})."
            ),
        )

    # ✅ Create complaint if unique
    complaint = Complaint(**complaint_data.dict(), created_by=_user.id)
    db.add(complaint)
    await db.flush()

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Created complaint '{complaint.title}' (ID: {complaint.id})",
    )

    await db.commit()
    await db.refresh(complaint)

    # ✅ Build serialized response dict
    return {
        "id": complaint.id,
        "customer_id": complaint.customer_id,
        "customer_name": complaint.customer.name if complaint.customer else "N/A",
        "customer_phone": complaint.customer.phone if complaint.customer else None,
        "invoice_id": complaint.invoice_id,
        "sales_order_id": complaint.sales_order_id,
        "quotation_id": complaint.quotation_id,
        "product_id": complaint.product_id,
        "title": complaint.title,
        "description": complaint.description,
        "status": complaint.status,
        "priority": complaint.priority,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
    }




# 📋 Get All Complaints (with filters)
async def get_all_complaints(
    db: AsyncSession,
    status=None,
    priority=None,
    customer_id=None,
    date_from: datetime = None,
    date_to: datetime = None,
    search: str = None,
    limit: int = 25,
    offset: int = 0,
):
    filters = [Complaint.is_deleted == False]

    if status:
        filters.append(Complaint.status == status)
    if priority:
        filters.append(Complaint.priority == priority)
    if customer_id:
        filters.append(Complaint.customer_id == customer_id)
    if date_from:
        filters.append(Complaint.created_at >= date_from)
    if date_to:
        filters.append(Complaint.created_at <= date_to)
    if search:
        search_like = f"%{search.lower()}%"
        filters.append(
            or_(
                Complaint.title.ilike(search_like),
                Complaint.description.ilike(search_like),
            )
        )

    stmt = (
        select(Complaint)
        .where(and_(*filters))
        .order_by(Complaint.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    return result.unique().scalars().all()


# 🔍 Get Single Complaint
async def get_complaint_by_id(db: AsyncSession, complaint_id: int):
    result = await db.execute(
        select(Complaint).where(
            Complaint.id == complaint_id, Complaint.is_deleted == False
        )
    )
    return result.unique().scalar_one_or_none()


# ✏️ Update Complaint
async def update_complaint(db: AsyncSession, complaint_id: int, data: ComplaintUpdate, _user: User):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None

    for key, value in data.dict(exclude_unset=True).items():
        setattr(complaint, key, value)

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Updated complaint #{complaint.id} by user '{_user.username}'",
    )
    await db.commit()
    await db.refresh(complaint)
    return complaint


# 🗑️ Soft Delete Complaint
async def delete_complaint(db: AsyncSession, complaint_id: int, _user: User):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None

    complaint.is_deleted = True
    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Soft-deleted complaint #{complaint.id} by user '{_user.username}'",
    )
    await db.commit()
    await db.refresh(complaint)
    return complaint
