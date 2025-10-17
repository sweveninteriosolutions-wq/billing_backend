from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.inventory_models import Supplier
from app.schemas.inventory_schemas import SupplierCreate, SupplierUpdate, SupplierOut, MessageResponse

# --------------------------
# Supplier Services
# --------------------------
async def create_supplier(db: AsyncSession, data: SupplierCreate) -> dict:
    existing = await db.execute(select(Supplier).where(Supplier.name == data.name, Supplier.is_deleted == False))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Supplier '{data.name}' already exists")

    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return {"message": "Supplier created successfully", "data": SupplierOut.model_validate(supplier)}

async def get_all_suppliers(db: AsyncSession) -> dict:
    result = await db.execute(select(Supplier).where(Supplier.is_deleted == False))
    suppliers = result.scalars().all()
    return {"message": "Suppliers fetched successfully", "data": [SupplierOut.model_validate(s) for s in suppliers]}

async def get_supplier(db: AsyncSession, supplier_id: int) -> dict:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier fetched successfully", "data": SupplierOut.model_validate(supplier)}

async def update_supplier(db: AsyncSession, supplier_id: int, data: SupplierUpdate) -> dict:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    if data.name and data.name != supplier.name:
        existing_name_check = await db.execute(
            select(Supplier).where(Supplier.name == data.name, Supplier.id != supplier_id, Supplier.is_deleted == False)
        )
        if existing_name_check.scalars().first():
            raise HTTPException(status_code=400, detail=f"Supplier '{data.name}' already exists")
        supplier.name = data.name

    for key, value in data.model_dump(exclude_unset=True).items():
        if key != "name":
            setattr(supplier, key, value)

    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return {"message": "Supplier updated successfully", "data": SupplierOut.model_validate(supplier)}

async def delete_supplier(db: AsyncSession, supplier_id: int) -> MessageResponse:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.is_deleted == False))
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    supplier.is_deleted = True
    db.add(supplier)
    await db.commit()
    return {"message": "Supplier deleted successfully"}
