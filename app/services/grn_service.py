from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.inventory_models import Product, GRN, GRNItem
from app.schemas.inventory_schemas import GRNCreate, GRNOut

# --------------------------
# GRN Services
# --------------------------
async def create_grn(db: AsyncSession, grn_data: GRNCreate, created_by: str) -> dict:
    # Ensure all products exist
    product_ids = [item.product_id for item in grn_data.items]
    result = await db.execute(select(Product.id).where(Product.id.in_(product_ids), Product.is_deleted == False))
    found_product_ids = {p_id for p_id, in result.all()}

    missing_products = set(product_ids) - found_product_ids
    if missing_products:
        raise HTTPException(status_code=404, detail=f"Products with IDs {list(missing_products)} not found.")

    if grn_data.bill_number:
        existing_bill = await db.execute(select(GRN).where(GRN.bill_number == grn_data.bill_number, GRN.is_deleted == False))
        if existing_bill.scalars().first():
            raise HTTPException(status_code=400, detail=f"GRN with bill number '{grn_data.bill_number}' already exists")

    sub_total = sum([item.quantity * item.price for item in grn_data.items])
    grn = GRN(
        supplier_id=grn_data.supplier_id,
        purchase_order=grn_data.purchase_order,
        sub_total=sub_total,
        total_amount=sub_total,
        notes=grn_data.notes,
        bill_number=grn_data.bill_number,
        bill_file=grn_data.bill_file,
        created_by=created_by,
        status="pending"
    )
    db.add(grn)
    await db.flush()

    for item in grn_data.items:
        grn_item = GRNItem(
            grn_id=grn.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            total=item.quantity * item.price
        )
        db.add(grn_item)

    await db.commit()
    result = await db.execute(select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn.id, GRN.is_deleted == False))
    grn_full = result.scalars().first()
    return {"message": "GRN created successfully", "data": GRNOut.model_validate(grn_full)}

async def get_all_grns(db: AsyncSession) -> dict:
    result = await db.execute(
        select(GRN)
        .where(GRN.is_deleted == False)
        .options(selectinload(GRN.items))
    )
    grns = result.scalars().all()
    return {"message": "GRNs fetched successfully", "data": [GRNOut.model_validate(g) for g in grns]}

async def verify_grn(db: AsyncSession, grn_id: int, verifier: str) -> dict:
    result = await db.execute(select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn_id, GRN.is_deleted == False))
    grn = result.scalars().first()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")
    if grn.status == "completed":
        raise HTTPException(status_code=400, detail="GRN already verified")

    # Update stock
    product_ids = [item.product_id for item in grn.items]
    result = await db.execute(select(Product).where(Product.id.in_(product_ids), Product.is_deleted == False))
    products_map = {p.id: p for p in result.scalars().all()}

    for item in grn.items:
        product = products_map.get(item.product_id)
        if product:
            product.quantity_warehouse += item.quantity
            db.add(product)

    grn.status = "completed"
    grn.verified_by = verifier
    db.add(grn)
    await db.commit()
    await db.refresh(grn)
    return {"message": "GRN verified successfully", "data": GRNOut.model_validate(grn)}

async def delete_grn(db: AsyncSession, grn_id: int) -> dict:
    result = await db.execute(select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn_id, GRN.is_deleted == False))
    grn = result.scalars().first()
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    # Revert stock if verified
    if grn.status == "completed":
        product_ids = [item.product_id for item in grn.items]
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products_map = {p.id: p for p in result.scalars().all()}

        for item in grn.items:
            product = products_map.get(item.product_id)
            if product and not product.is_deleted:
                product.quantity_warehouse -= item.quantity
                db.add(product)

    grn.is_deleted = True
    db.add(grn)
    await db.commit()
    return {"message": "GRN deleted successfully"}
