# app/services/stock_transfer_services.py

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime

from app.models.stock_transfer_models import StockTransfer, TransferStatus
from app.models.product_models import Product
from app.schemas.stock_transfer_schemas import StockTransferCreate, StockTransferUpdate
from app.utils.activity_helpers import log_user_activity


# ---------------------------------------------------
# CREATE STOCK TRANSFER
# ---------------------------------------------------
async def create_stock_transfer(db: AsyncSession, data: StockTransferCreate, current_user):
    """
    Create a stock transfer and temporarily deduct stock from source location.
    """
    product = await db.get(Product, data.product_id)
    if not product or product.is_deleted:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate quantity
    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    # Check available stock
    if data.from_location == "showroom":
        available = product.quantity_showroom
    else:
        available = product.quantity_warehouse

    if available < data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock at source location")

    # Deduct stock temporarily
    if data.from_location == "showroom":
        product.quantity_showroom -= data.quantity
    else:
        product.quantity_warehouse -= data.quantity

    # Create transfer record
    transfer = StockTransfer(
        product_id=data.product_id,
        quantity=data.quantity,
        from_location=data.from_location,
        to_location=data.to_location,
        status=TransferStatus.pending,
        transferred_by=current_user.id,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add_all([transfer, product])

    # Log action
    await log_user_activity(
        db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"Created stock transfer (ID: {transfer.id}) from {data.from_location} to {data.to_location}"
    )

    await db.commit()
    await db.refresh(transfer)
    return transfer


# ---------------------------------------------------
# COMPLETE STOCK TRANSFER
# ---------------------------------------------------
async def complete_stock_transfer(db: AsyncSession, transfer_id: int, current_user):
    """
    Complete a pending stock transfer and update destination stock.
    """
    transfer = await db.get(StockTransfer, transfer_id)
    if not transfer or transfer.is_deleted:
        raise HTTPException(status_code=404, detail="Transfer not found")

    if transfer.status != TransferStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending transfers can be completed")

    product = await db.get(Product, transfer.product_id)

    # Add stock to destination
    if transfer.to_location == "showroom":
        product.quantity_showroom += transfer.quantity
    else:
        product.quantity_warehouse += transfer.quantity

    transfer.status = TransferStatus.completed
    transfer.completed_by = current_user.id
    transfer.completed_at = datetime.utcnow()
    transfer.updated_by = current_user.id

    db.add_all([transfer, product])

    # Log action
    await log_user_activity(
        db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"Completed stock transfer (ID: {transfer.id}) for product ID {transfer.product_id}"
    )

    await db.commit()
    await db.refresh(transfer)
    return transfer


# ---------------------------------------------------
# UPDATE STOCK TRANSFER
# ---------------------------------------------------
async def update_stock_transfer(db: AsyncSession, transfer_id: int, data: StockTransferUpdate, current_user):
    """
    Update stock transfer details, including status, if allowed.
    """
    transfer = await db.get(StockTransfer, transfer_id)
    if not transfer or transfer.is_deleted:
        raise HTTPException(status_code=404, detail="Transfer not found")

    if transfer.status == TransferStatus.completed:
        raise HTTPException(status_code=400, detail="Cannot update a completed transfer")

    if data.status:
        # Validate allowed status transitions
        valid_transitions = {
            TransferStatus.pending: [TransferStatus.cancelled, TransferStatus.completed],
            TransferStatus.cancelled: [],
            TransferStatus.completed: [],
        }
        if data.status not in valid_transitions.get(transfer.status, []):
            raise HTTPException(status_code=400, detail="Invalid status transition")
        transfer.status = data.status

    if data.completed_by:
        transfer.completed_by = data.completed_by

    transfer.updated_by = current_user.id
    db.add(transfer)

    # Log update
    await log_user_activity(
        db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"Updated stock transfer (ID: {transfer.id}) status to {transfer.status}"
    )

    await db.commit()
    await db.refresh(transfer)
    return transfer


# ---------------------------------------------------
# GET SINGLE STOCK TRANSFER
# ---------------------------------------------------
async def get_stock_transfer(db: AsyncSession, transfer_id: int):
    """
    Retrieve a single stock transfer by ID.
    """
    result = await db.execute(
        select(StockTransfer).where(StockTransfer.id == transfer_id, StockTransfer.is_deleted == False)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


# ---------------------------------------------------
# GET ALL STOCK TRANSFERS (with filters + pagination)
# ---------------------------------------------------
async def get_all_stock_transfers(db: AsyncSession, status: str = None, page: int = 1, page_size: int = 10):
    """
    Retrieve all stock transfers with optional status filter and pagination.
    """
    query = select(StockTransfer).where(StockTransfer.is_deleted == False)
    if status:
        query = query.where(StockTransfer.status == status)

    query = query.order_by(StockTransfer.created_at.desc())
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    transfers = result.scalars().all()
    return transfers


# ---------------------------------------------------
# DELETE STOCK TRANSFER
# ---------------------------------------------------
async def delete_stock_transfer(db: AsyncSession, transfer_id: int, current_user):
    """
    Soft-delete a pending stock transfer only.
    """
    transfer = await db.get(StockTransfer, transfer_id)
    if not transfer or transfer.is_deleted:
        raise HTTPException(status_code=404, detail="Transfer not found")

    if transfer.status != TransferStatus.pending:
        raise HTTPException(status_code=400, detail="Cannot delete verified or completed transfers.")

    transfer.is_deleted = True
    transfer.updated_by = current_user.id
    db.add(transfer)

    # Log deletion
    await log_user_activity(
        db,
        user_id=current_user.id,
        username=current_user.username,
        message=f"Deleted stock transfer (ID: {transfer.id})"
    )

    await db.commit()
    return {"message": "Stock transfer deleted successfully."}
