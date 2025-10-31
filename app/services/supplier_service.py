# app/services/supplier_services.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, DataError
from app.models.supplier_models import Supplier
from app.schemas.supplier_schemas import SupplierCreate, SupplierUpdate, SupplierOut
from app.utils.activity_helpers import log_user_activity
from app.models.grn_models import GRN
from app.models.product_models import Product
from app.models.supplier_models import Supplier


from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.exc import SQLAlchemyError

ALLOWED_SORT_FIELDS = {
    "id": Supplier.id,
    "name": Supplier.name,
    "contact_person": Supplier.contact_person,
    "created_at": Supplier.created_at,
}


# ---------------------------
# CREATE SUPPLIER
# ---------------------------
async def create_supplier(db: AsyncSession, data: SupplierCreate, current_user) -> dict:
    try:
        # 🔍 Check if supplier already exists (not deleted)
        existing = await db.execute(
            select(Supplier).where(Supplier.name == data.name, Supplier.is_deleted == False)
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Supplier '{data.name}' already exists"
            )

        # ✅ Create supplier
        supplier = Supplier(**data.model_dump())
        supplier.created_by_id = current_user.id

        db.add(supplier)
        await db.flush()

        # 📝 Log activity
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} created supplier '{supplier.name}' (ID: {supplier.id})"
        )

        await db.commit()
        await db.refresh(supplier)

        return {
            "message": "Supplier created successfully",
            "data": SupplierOut.model_validate(supplier)
        }

    except IntegrityError as e:
        # ⚠️ Catch UNIQUE constraint errors safely
        await db.rollback()
        if "UNIQUE constraint failed" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Supplier with the same name already exists."
            )
        raise HTTPException(status_code=400, detail="Database integrity error")

    except HTTPException:
        # Let existing HTTP errors (like 422 above) bubble up cleanly
        raise

    except Exception as e:
        # 🧨 Catch all others
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

#-----------------------------------
# GET ALL SUPPLIERS (with filters, pagination, sorting)
# ---------------------------
async def get_all_suppliers(
    db: AsyncSession,
    search: str = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    order: str = "desc",
) -> dict:
    try:
        sort_column = ALLOWED_SORT_FIELDS.get(sort_by, Supplier.created_at)
        sort_order = desc(sort_column) if order.lower() == "desc" else asc(sort_column)

        stmt = select(Supplier).where(Supplier.is_deleted == False)
        count_stmt = select(func.count(Supplier.id)).where(Supplier.is_deleted == False)

        if search:
            stmt = stmt.where(
                or_(
                    Supplier.name.ilike(f"%{search}%"),
                    Supplier.contact_person.ilike(f"%{search}%"),
                )
            )
            count_stmt = count_stmt.where(
                or_(
                    Supplier.name.ilike(f"%{search}%"),
                    Supplier.contact_person.ilike(f"%{search}%"),
                )
            )

        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(sort_order).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        suppliers = result.scalars().all()

        return {
            "message": "Suppliers fetched successfully",
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": [SupplierOut.model_validate(s) for s in suppliers],
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e.orig))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ---------------------------
# GET SINGLE SUPPLIER
# ---------------------------
async def get_supplier(db: AsyncSession, supplier_id: int) -> dict:
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
    )
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier fetched successfully", "data": SupplierOut.model_validate(supplier)}


# ---------------------------
# UPDATE SUPPLIER
# ---------------------------
async def update_supplier(db: AsyncSession, supplier_id: int, data: SupplierUpdate, current_user) -> dict:
    # Fetch existing supplier
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
    )
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Check for duplicate name if name is being updated
    if data.name and data.name != supplier.name:
        existing = await db.execute(
            select(Supplier).where(Supplier.name == data.name, Supplier.is_deleted == False)
        )
        duplicate = existing.scalars().first()
        if duplicate:
            raise HTTPException(status_code=400, detail=f"Supplier name '{data.name}' already exists")

    changes = []
    for key, value in data.model_dump(exclude_unset=True).items():
        old_val = getattr(supplier, key)
        if old_val != value:
            changes.append(f"{key}: {old_val} → {value}")
            setattr(supplier, key, value)

    supplier.updated_by_id = current_user.id
    db.add(supplier)

    if current_user and changes:
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} updated supplier '{supplier.name}' — {', '.join(changes)}"
        )

    await db.commit()
    await db.refresh(supplier)

    return {"message": "Supplier updated successfully", "data": SupplierOut.model_validate(supplier)}


# ---------------------------
# DELETE SUPPLIER
# ---------------------------
async def delete_supplier(db: AsyncSession, supplier_id: int, current_user) -> dict:
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
    )
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier.is_deleted = True
    db.add(supplier)
    await log_user_activity(
        db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"{current_user.role.capitalize()} deleted supplier '{supplier.name}' (ID: {supplier.id})"
    )
    await db.commit()



    return {"message": "Supplier deleted successfully"}
