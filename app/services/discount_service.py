from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.discount_models import Discount
from app.schemas.discount_schemas import DiscountCreate, DiscountUpdate
from app.utils.activity_helpers import log_user_activity
from fastapi import HTTPException
from sqlalchemy import select, and_, or_

# -----------------------
# CREATE
# -----------------------
async def create_discount(db: AsyncSession, payload: DiscountCreate, _user):
    # Validate dates
    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    # Duplicate code check (only active ones)
    existing = await db.execute(
        select(Discount).where(Discount.code == payload.code, Discount.is_deleted == False)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Discount code already exists")

    # Validate discount value
    if payload.discount_type == "percentage" and not (0 < float(payload.discount_value) <= 100):
        raise HTTPException(status_code=400, detail="Percentage discount must be between 0 and 100")

    if payload.discount_type == "flat" and payload.discount_value <= 0:
        raise HTTPException(status_code=400, detail="Flat discount must be greater than 0")

    discount = Discount(**payload.dict())
    db.add(discount)
    await db.flush()

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Created discount '{discount.name}' ({discount.code})"
    )

    await db.commit()
    await db.refresh(discount)
    return discount


# -----------------------
# READ
# -----------------------
async def get_all_discounts(
    db: AsyncSession,
    status: str | None = None,
    code: str | None = None,
    name: str | None = None,
    discount_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    include_deleted: bool = False,
):
    filters = []

    # Soft delete filter
    if not include_deleted:
        filters.append(Discount.is_deleted == False)

    # Status filter
    if status:
        if status.lower() == "deleted":
            filters.append(Discount.is_deleted == True)
        else:
            filters.append(Discount.status.ilike(status))

    # Code / Name partial match
    if code:
        filters.append(Discount.code.ilike(f"%{code}%"))
    if name:
        filters.append(Discount.name.ilike(f"%{name}%"))

    # Type filter
    if discount_type:
        filters.append(Discount.discount_type.ilike(discount_type))

    # Date range filters
    if start_date:
        filters.append(Discount.start_date >= start_date)
    if end_date:
        filters.append(Discount.end_date <= end_date)

    query = select(Discount).where(and_(*filters)).order_by(Discount.start_date.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_discount_by_id(db: AsyncSession, discount_id: int): 
    result = await db.execute( select(Discount).where(Discount.id == discount_id, Discount.is_deleted == False) ) 
    return result.scalar_one_or_none()

# -----------------------
# UPDATE
# -----------------------
async def update_discount(db: AsyncSession, discount_id: int, payload: DiscountUpdate, _user):
    discount = await get_discount_by_id(db, discount_id)
    if not discount:
        return None

    update_data = payload.dict(exclude_unset=True)

    if "start_date" in update_data and "end_date" in update_data:
        if update_data["start_date"] >= update_data["end_date"]:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

    if "discount_type" in update_data or "discount_value" in update_data:
        dtype = update_data.get("discount_type", discount.discount_type)
        dval = float(update_data.get("discount_value", discount.discount_value))
        if dtype == "percentage" and not (0 < dval <= 100):
            raise HTTPException(status_code=400, detail="Percentage discount must be between 0 and 100")
        if dtype == "flat" and dval <= 0:
            raise HTTPException(status_code=400, detail="Flat discount must be greater than 0")

    for key, value in update_data.items():
        setattr(discount, key, value)

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Updated discount '{discount.name}' (ID: {discount.id})"
    )

    await db.commit()
    await db.refresh(discount)
    return discount


# -----------------------
# SOFT DELETE
# -----------------------
async def delete_discount(db: AsyncSession, discount_id: int, _user):
    discount = await get_discount_by_id(db, discount_id)
    if not discount:
        return None

    discount.is_deleted = True
    discount.status = "inactive"

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Soft-deleted discount '{discount.name}' (ID: {discount.id})"
    )

    await db.commit()
    await db.refresh(discount)
    return discount


# -----------------------
# REACTIVATE
# -----------------------
async def reactivate_discount(db: AsyncSession, discount_id: int, _user):
    # Fetch even if deleted
    result = await db.execute(select(Discount).where(Discount.id == discount_id))
    discount = result.scalar_one_or_none()

    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    # Prevent reactivating an already active discount
    if not discount.is_deleted:
        raise HTTPException(status_code=400, detail="Discount is already active")

    # Optional: validate date range — ensure not expired before reactivation
    if discount.end_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot reactivate expired discount")

    # Reactivate it
    discount.is_deleted = False
    discount.status = "active"

    await log_user_activity(
        db=db,
        user_id=_user.id,
        username=_user.username,
        message=f"Reactivated discount '{discount.name}' (ID: {discount.id})"
    )

    await db.commit()
    await db.refresh(discount)
    return discount
