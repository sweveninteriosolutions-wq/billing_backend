# app/services/inventory_services/grn_service.py
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.grn_models import GRN, GRNItem
from app.models.product_models import Product
from app.models.supplier_models import Supplier




from app.schemas.inventory_schemas import GRNCreate, GRNOut
from app.utils.activity_helpers import log_user_activity


# --------------------------
# CREATE GRN
# --------------------------
async def create_grn(db: AsyncSession, grn_data: GRNCreate, current_user) -> dict:
    """
    Create a GRN ensuring only active products and supplier are used.
    """
    try:
        # ✅ Check active supplier
        result = await db.execute(
            select(Supplier).where(Supplier.id == grn_data.supplier_id, Supplier.is_deleted == False)
        )
        supplier = result.scalars().first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found or inactive")

        # ✅ Ensure all products exist and are active
        product_ids = [item.product_id for item in grn_data.items]
        result = await db.execute(
            select(Product.id).where(Product.id.in_(product_ids), Product.is_deleted == False)
        )
        active_product_ids = {p_id for p_id, in result.all()}
        missing_products = set(product_ids) - active_product_ids
        if missing_products:
            raise HTTPException(status_code=404, detail=f"Products with IDs {list(missing_products)} not found or inactive")

        # ✅ Check bill number uniqueness if provided
        if grn_data.bill_number:
            existing_bill = await db.execute(
                select(GRN).where(GRN.bill_number == grn_data.bill_number, GRN.is_deleted == False)
            )
            if existing_bill.scalars().first():
                raise HTTPException(status_code=422, detail=f"GRN with bill number '{grn_data.bill_number}' already exists")

        # Calculate totals
        sub_total = sum(item.quantity * item.price for item in grn_data.items)
        grn = GRN(
            supplier_id=grn_data.supplier_id,
            purchase_order=grn_data.purchase_order,
            sub_total=sub_total,
            total_amount=sub_total,
            notes=grn_data.notes,
            bill_number=grn_data.bill_number,
            bill_file=grn_data.bill_file,
            created_by=current_user.id,
            status="pending"
        )
        db.add(grn)
        await db.flush()  # Ensure GRN ID available

        # Add GRN items
        for item in grn_data.items:
            grn_item = GRNItem(
                grn_id=grn.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total=item.quantity * item.price
            )
            db.add(grn_item)

        # ✅ Log activity before commit
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.username} created GRN '{grn.bill_number or grn.id}' with {len(grn_data.items)} items"
        )

        await db.commit()

        # Return full GRN with items
        result = await db.execute(
            select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn.id, GRN.is_deleted == False)
        )
        grn_full = result.scalars().first()
        return {"message": "GRN created successfully", "data": GRNOut.model_validate(grn_full)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating GRN: {e}")


# --------------------------
# GET ALL GRNs
# --------------------------
async def get_all_grns(db: AsyncSession) -> dict:
    result = await db.execute(
        select(GRN).where(GRN.is_deleted == False).options(selectinload(GRN.items))
    )
    grns = result.scalars().all()
    return {"message": "GRNs fetched successfully", "data": [GRNOut.model_validate(g) for g in grns]}


# --------------------------
# VERIFY GRN
# --------------------------
async def verify_grn(db: AsyncSession, grn_id: int, current_user) -> dict:
    """
    Verify GRN and update warehouse stock. Only active products considered.
    """
    try:
        result = await db.execute(
            select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn_id, GRN.is_deleted == False)
        )
        grn = result.scalars().first()
        if not grn:
            raise HTTPException(status_code=404, detail="GRN not found")
        if grn.status == "completed":
            raise HTTPException(status_code=422, detail="GRN already verified")

        # Update stock for active products
        product_ids = [item.product_id for item in grn.items]
        result = await db.execute(select(Product).where(Product.id.in_(product_ids), Product.is_deleted == False))
        products_map = {p.id: p for p in result.scalars().all()}

        for item in grn.items:
            product = products_map.get(item.product_id)
            if product:
                product.quantity_warehouse += item.quantity
                db.add(product)

        grn.status = "completed"
        grn.verified_by = current_user.id
        db.add(grn)

        # ✅ Log verification
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.username} verified GRN '{grn.bill_number or grn.id}'"
        )

        await db.commit()
        await db.refresh(grn)
        return {"message": "GRN verified successfully", "data": GRNOut.model_validate(grn)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error verifying GRN: {e}")


# --------------------------
# DELETE GRN
# --------------------------
async def delete_grn(db: AsyncSession, grn_id: int, current_user) -> dict:
    """
    Soft-delete GRN and revert stock if verified.
    Only active products are updated.
    """
    try:
        result = await db.execute(
            select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn_id, GRN.is_deleted == False)
        )
        grn = result.scalars().first()
        if not grn:
            raise HTTPException(status_code=404, detail="GRN not found")

        # Revert stock for active products if GRN was verified
        if grn.status == "completed":
            product_ids = [item.product_id for item in grn.items]
            result = await db.execute(select(Product).where(Product.id.in_(product_ids), Product.is_deleted == False))
            products_map = {p.id: p for p in result.scalars().all()}
            for item in grn.items:
                product = products_map.get(item.product_id)
                if product:
                    product.quantity_warehouse -= item.quantity
                    db.add(product)

        grn.is_deleted = True
        db.add(grn)

        # ✅ Log deletion
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.username} deleted GRN '{grn.bill_number or grn.id}'"
        )

        await db.commit()
        return {"message": "GRN deleted successfully"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting GRN: {e}")
