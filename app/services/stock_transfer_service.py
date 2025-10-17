from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.inventory_models import Product, StockTransfer
from app.schemas.inventory_schemas import TransferCreate, TransferUpdate, TransferOut

# --------------------------
# Stock Transfer Services
# --------------------------
async def create_stock_transfer(db: AsyncSession, transfer_data: TransferCreate, transferred_by: int) -> dict:
    result = await db.execute(select(Product).where(Product.id == transfer_data.product_id, Product.is_deleted == False))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if transfer_data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    
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
        transferred_by=transferred_by,
        transfer_date=datetime.now(timezone.utc)
    )
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    return {"message": "Stock transfer created successfully", "data": TransferOut.model_validate(transfer)}

async def get_stock_transfer(db: AsyncSession, transfer_id: int) -> dict:
    result = await db.execute(select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False))
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return {"message": "Stock transfer fetched successfully", "data": TransferOut.model_validate(transfer)}

async def update_stock_transfer(db: AsyncSession, transfer_id: int, data: TransferUpdate) -> dict:
    result = await db.execute(select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False))
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        if key in ["quantity", "from_location", "to_location"]:
            setattr(transfer, key, value)

    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    return {"message": "Stock transfer updated successfully", "data": TransferOut.model_validate(transfer)}

async def delete_stock_transfer(db: AsyncSession, transfer_id: int) -> dict:
    # Fetch transfer
    result = await db.execute(
        select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    # Fetch associated product
    result = await db.execute(
        select(Product).where(Product.id == transfer.product_id, Product.is_deleted == False)
    )
    product = result.scalars().first()

    # Revert stock quantities only if product exists
    if product and transfer.status == "completed":
        # Check if reverting will result in negative stock
        if transfer.to_location == "warehouse":
            if product.quantity_warehouse < transfer.quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete transfer: warehouse stock would go negative"
                )
            product.quantity_warehouse -= transfer.quantity
        else:
            if product.quantity_showroom < transfer.quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete transfer: showroom stock would go negative"
                )
            product.quantity_showroom -= transfer.quantity

        if transfer.from_location == "warehouse":
            product.quantity_warehouse += transfer.quantity
        else:
            product.quantity_showroom += transfer.quantity

        db.add(product)  # safe, product is not None

    # Mark transfer as deleted
    transfer.is_deleted = True
    db.add(transfer)
    await db.commit()

    return {"message": "Stock transfer deleted successfully"}


async def get_all_stock_transfers(db: AsyncSession) -> dict:
    result = await db.execute(select(StockTransfer).where(StockTransfer.is_deleted == False))
    transfers = result.scalars().all()
    return {"message": "Stock transfers fetched successfully", "data": [TransferOut.model_validate(t) for t in transfers]}

async def complete_stock_transfer(db: AsyncSession, transfer_id: int, completed_by: int) -> dict:
    # Fetch the transfer
    result = await db.execute(
        select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    if transfer.status == "completed":
        raise HTTPException(status_code=400, detail="Transfer already completed")

    if transfer.from_location == transfer.to_location:
        raise HTTPException(status_code=400, detail="From and to locations cannot be the same.")

    # Fetch the product
    result = await db.execute(
        select(Product).where(Product.id == transfer.product_id, Product.is_deleted == False)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found for this stock transfer")

    # Check stock availability and update quantities
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

    # Mark transfer as completed
    transfer.status = "completed"
    transfer.completed_by = completed_by
    transfer.completed_at = datetime.now(timezone.utc)

    # Persist changes
    db.add(product)
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)

    return {"message": "Stock transfer completed successfully", "data": TransferOut.model_validate(transfer)}
