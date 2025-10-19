from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, DataError

from app.models.inventory_models import Supplier
from app.schemas.inventory_schemas import SupplierCreate, SupplierUpdate, SupplierOut
from app.utils.activity_helpers import log_user_activity


# ---------------------------
# CREATE SUPPLIER
# ---------------------------
async def create_supplier(db: AsyncSession, data: SupplierCreate, current_user) -> dict:
    try:
        # Check uniqueness
        existing = await db.execute(
            select(Supplier).where(Supplier.name == data.name, Supplier.is_deleted == False)
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Supplier '{data.name}' already exists"
            )

        supplier = Supplier(**data.model_dump())
        db.add(supplier)
        await db.flush()  # ensures supplier.id is available

        # Log creation
        if current_user:
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} created supplier '{supplier.name}' (ID: {supplier.id})"
            )

        await db.commit()
        await db.refresh(supplier)
        return {"message": "Supplier created successfully", "data": SupplierOut.model_validate(supplier)}

    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e.orig))
    except DataError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ---------------------------
# GET ALL SUPPLIERS
# ---------------------------
async def get_all_suppliers(db: AsyncSession) -> dict:
    try:
        result = await db.execute(select(Supplier).where(Supplier.is_deleted == False))
        suppliers = result.scalars().all()
        return {
            "message": "Suppliers fetched successfully",
            "data": [SupplierOut.model_validate(s) for s in suppliers],
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ---------------------------
# GET SINGLE SUPPLIER
# ---------------------------
async def get_supplier(db: AsyncSession, supplier_id: int) -> dict:
    try:
        result = await db.execute(
            select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
        )
        supplier = result.scalars().first()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        return {"message": "Supplier fetched successfully", "data": SupplierOut.model_validate(supplier)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ---------------------------
# UPDATE SUPPLIER
# ---------------------------
async def update_supplier(db: AsyncSession, supplier_id: int, data: SupplierUpdate, current_user) -> dict:
    try:
        result = await db.execute(
            select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
        )
        supplier = result.scalars().first()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

        changes = []

        # Name change
        if data.name and data.name != supplier.name:
            existing_name_check = await db.execute(
                select(Supplier).where(
                    Supplier.name == data.name,
                    Supplier.id != supplier_id,
                    Supplier.is_deleted == False
                )
            )
            if existing_name_check.scalars().first():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Supplier '{data.name}' already exists")
            changes.append(f"name: {supplier.name} → {data.name}")
            supplier.name = data.name

        # Other fields
        for key, value in data.model_dump(exclude_unset=True).items():
            if key != "name":
                old_val = getattr(supplier, key)
                if old_val != value:
                    changes.append(f"{key}: {old_val} → {value}")
                    setattr(supplier, key, value)

        db.add(supplier)
        await db.refresh(supplier)

        # Log changes
        if current_user and changes:
            change_summary = ", ".join(changes)
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} updated supplier '{supplier.name}' "
                        f"(ID: {supplier.id}) — {change_summary}"
            )
            await db.commit()

        return {"message": "Supplier updated successfully", "data": SupplierOut.model_validate(supplier)}

    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e.orig))
    except DataError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ---------------------------
# DELETE SUPPLIER
# ---------------------------
async def delete_supplier(db: AsyncSession, supplier_id: int, current_user) -> dict:
    try:
        result = await db.execute(
            select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False)
        )
        supplier = result.scalars().first()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

        supplier.is_deleted = True
        db.add(supplier)

        # Log deletion
        if current_user:
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} deleted supplier '{supplier.name}' (ID: {supplier.id})"
            )
            await db.commit()

        return {"message": "Supplier deleted successfully"}

    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e.orig))
    except DataError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.orig))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
