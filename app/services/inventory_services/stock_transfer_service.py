# app/services/inventory_services/stock_transfer_service.py
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.inventory_models import Product, StockTransfer
from app.schemas.inventory_schemas import TransferCreate, TransferUpdate, TransferOut
from app.utils.activity_helpers import log_user_activity


# --------------------------
# CREATE STOCK TRANSFER
# --------------------------
async def create_stock_transfer(db: AsyncSession, transfer_data: TransferCreate, current_user) -> dict:
    try:
        # ✅ Only active products allowed
        result = await db.execute(
            select(Product).where(Product.id == transfer_data.product_id, Product.is_deleted == False)
        )
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found or inactive")

        if transfer_data.quantity <= 0:
            raise HTTPException(status_code=422, detail="Quantity must be positive")

        if transfer_data.from_location == "warehouse" and product.quantity_warehouse < transfer_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient warehouse stock")
        if transfer_data.from_location == "showroom" and product.quantity_showroom < transfer_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient showroom stock")

        transfer = StockTransfer(
            product_id=transfer_data.product_id,
            quantity=transfer_data.quantity,
            from_location=transfer_data.from_location,
            to_location=transfer_data.to_location,
            status="pending",
            transferred_by=current_user.id,
            transfer_date=datetime.now(timezone.utc)
        )
        db.add(transfer)

        # ✅ Log creation
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.username} created stock transfer for product ID {transfer.product_id}, qty {transfer.quantity}"
        )

        await db.commit()
        await db.refresh(transfer)
        return {"message": "Stock transfer created successfully", "data": TransferOut.model_validate(transfer)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating stock transfer: {e}")


# --------------------------
# GET SINGLE STOCK TRANSFER
# --------------------------
async def get_stock_transfer(db: AsyncSession, transfer_id: int) -> dict:
    result = await db.execute(
        select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return {"message": "Stock transfer fetched successfully", "data": TransferOut.model_validate(transfer)}


# --------------------------
# GET ALL STOCK TRANSFERS
# --------------------------
async def get_all_stock_transfers(db: AsyncSession) -> dict:
    result = await db.execute(
        select(StockTransfer).where(StockTransfer.is_deleted == False)
    )
    transfers = result.scalars().all()
    return {"message": "Stock transfers fetched successfully", "data": [TransferOut.model_validate(t) for t in transfers]}


# --------------------------
# UPDATE STOCK TRANSFER
# --------------------------
async def update_stock_transfer(db: AsyncSession, transfer_id: int, data: TransferUpdate, current_user) -> dict:
    try:
        result = await db.execute(
            select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
        )
        transfer = result.scalars().first()
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")

        changes = []
        for key, value in data.model_dump(exclude_unset=True).items():
            old_val = getattr(transfer, key, None)
            if old_val != value:
                setattr(transfer, key, value)
                changes.append(f"{key}: {old_val} → {value}")

        db.add(transfer)
        await db.commit()
        await db.refresh(transfer)

        # ✅ Log changes
        if changes:
            change_summary = ", ".join(changes)
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.username} updated stock transfer ID {transfer.id} — {change_summary}"
            )
            await db.commit()

        return {"message": "Stock transfer updated successfully", "data": TransferOut.model_validate(transfer)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating stock transfer: {e}")


# --------------------------
# COMPLETE STOCK TRANSFER
# --------------------------
async def complete_stock_transfer(db: AsyncSession, transfer_id: int, current_user) -> dict:
    try:
        result = await db.execute(
            select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
        )
        transfer = result.scalars().first()
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        if transfer.status == "completed":
            raise HTTPException(status_code=422, detail="Transfer already completed")

        # ✅ Only active product
        result = await db.execute(
            select(Product).where(Product.id == transfer.product_id, Product.is_deleted == False)
        )
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found or inactive")

        if transfer.from_location == transfer.to_location:
            raise HTTPException(status_code=400, detail="From and to locations cannot be the same.")

        if transfer.from_location == "warehouse":
            if product.quantity_warehouse < transfer.quantity:
                raise HTTPException(status_code=400, detail="Insufficient warehouse stock to complete transfer")
            product.quantity_warehouse -= transfer.quantity
        elif transfer.from_location == "showroom":
            if product.quantity_showroom < transfer.quantity:
                raise HTTPException(status_code=400, detail="Insufficient showroom stock to complete transfer")
            product.quantity_showroom -= transfer.quantity

        if transfer.to_location == "warehouse":
            product.quantity_warehouse += transfer.quantity
        elif transfer.to_location == "showroom":
            product.quantity_showroom += transfer.quantity

        transfer.status = "completed"
        transfer.completed_by = current_user.id
        transfer.completed_at = datetime.now(timezone.utc)

        db.add(product)
        db.add(transfer)

        # ✅ Log completion
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.username} completed stock transfer ID {transfer.id} for product ID {transfer.product_id}"
        )

        await db.commit()
        await db.refresh(transfer)
        return {"message": "Stock transfer completed successfully", "data": TransferOut.model_validate(transfer)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error completing stock transfer: {e}")


# --------------------------
# DELETE STOCK TRANSFER
# --------------------------
async def delete_stock_transfer(db: AsyncSession, transfer_id: int, current_user) -> dict:
    try:
        result = await db.execute(
            select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
        )
        transfer = result.scalars().first()
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")

        # ✅ Only revert stock for active products
        result = await db.execute(
            select(Product).where(Product.id == transfer.product_id, Product.is_deleted == False)
        )
        product = result.scalars().first()
        if product and transfer.status == "completed":
            if transfer.to_location == "warehouse":
                product.quantity_warehouse -= transfer.quantity
            elif transfer.to_location == "showroom":
                product.quantity_showroom -= transfer.quantity

            if transfer.from_location == "warehouse":
                product.quantity_warehouse += transfer.quantity
            elif transfer.from_location == "showroom":
                product.quantity_showroom += transfer.quantity

            db.add(product)

        transfer.is_deleted = True
        db.add(transfer)

        # ✅ Log deletion
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.username} deleted stock transfer ID {transfer.id} for product ID {transfer.product_id}"
        )

        await db.commit()
        return {"message": "Stock transfer deleted successfully"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting stock transfer: {e}")
