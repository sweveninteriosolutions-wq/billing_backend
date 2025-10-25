from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.models.billing_models.sales_order_models import SalesOrder
from app.models.billing_models.quotation_models import Quotation
from app.schemas.billing_schemas.sales_order_schema import SalesOrderResponse, QuotationDetailResponse


# =====================================================
# 🔹 CREATE SALES ORDER
# =====================================================
async def create_sales_order_from_quotation(db: AsyncSession, quotation_id: int) -> SalesOrderResponse:
    existing_order = await db.execute(select(SalesOrder).where(SalesOrder.quotation_id == quotation_id))
    existing_order = existing_order.scalars().first()
    if existing_order:
        raise HTTPException(status_code=409, detail="Sales Order already exists")

    result = await db.execute(
        select(Quotation)
        .where(Quotation.id == quotation_id)
        .options(selectinload(Quotation.customer), selectinload(Quotation.items))
    )
    quotation = result.scalars().first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    order = SalesOrder(
        quotation_id=quotation.id,
        customer_id=quotation.customer_id,
        customer_name=quotation.customer.name,
        quotation_items=[{
            "product_id": item.product_id,
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item.total,
        } for item in quotation.items],
        completion_status=[{
            "date": datetime.now(timezone.utc).isoformat(),
            "status": "arrived_from_quotation",
            "note": "Order received from quotation",
        }]
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return SalesOrderResponse.model_validate(order, from_attributes=True)


# =====================================================
# 🔹 APPROVE SALES ORDER
# =====================================================
async def approve_order(db: AsyncSession, order_id: int) -> SalesOrderResponse:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id).options(selectinload(SalesOrder.quotation))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.completion_flag:
        raise HTTPException(status_code=400, detail="Order not completed yet")

    if order.approved:
        raise HTTPException(status_code=409, detail="Order already approved")

    order.approved = True
    db.add(order)
    await db.commit()
    await db.refresh(order)

    return SalesOrderResponse.model_validate(order, from_attributes=True)


# =====================================================
# 🔹 UPDATE WORK STATUS
# =====================================================
async def update_work_status(db: AsyncSession, order_id: int, status: str, note: str) -> SalesOrderResponse:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id).options(selectinload(SalesOrder.quotation))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.completion_flag:
        raise HTTPException(status_code=409, detail="Cannot update work status of a completed order")

    order.completion_status.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "note": note
    })

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return SalesOrderResponse.model_validate(order, from_attributes=True)


# =====================================================
# 🔹 MARK SALES ORDER COMPLETE
# =====================================================
async def mark_sales_order_complete_service(db: AsyncSession, order_id: int) -> SalesOrderResponse:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id).options(selectinload(SalesOrder.quotation))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.completion_flag:
        raise HTTPException(status_code=409, detail="Sales order is already marked as complete")

    order.completion_flag = True
    order.completion_status.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "status": "Completed",
        "note": "Sales order marked as complete."
    })

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return SalesOrderResponse.model_validate(order, from_attributes=True)


# =====================================================
# 🔹 MOVE SALES ORDER TO INVOICE
# =====================================================
async def move_sales_order_to_invoice(db: AsyncSession, order_id: int) -> SalesOrderResponse:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id).options(selectinload(SalesOrder.quotation))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.completion_flag:
        raise HTTPException(status_code=400, detail="Order not completed yet")

    if not order.approved:
        raise HTTPException(status_code=400, detail="Order not approved yet")

    if order.moved_to_invoice:
        raise HTTPException(status_code=409, detail="Order already moved to invoice")

    order.moved_to_invoice = True
    db.add(order)
    await db.commit()
    await db.refresh(order)

    return SalesOrderResponse.model_validate(order, from_attributes=True)


# =====================================================
# 🔹 GET APPROVED OR MOVED QUOTATIONS
# =====================================================
async def get_approved_or_moved_quotations(db: AsyncSession) -> dict:
    """List approved or moved quotations excluding those with existing sales orders."""
    subquery = select(SalesOrder.quotation_id)
    result = await db.execute(
        select(Quotation)
        .options(selectinload(Quotation.items), selectinload(Quotation.customer))
        .where(
            or_(
                Quotation.approved == True,
                Quotation.moved_to_sales == True
            ),
            ~Quotation.id.in_(subquery)
        )
        .order_by(Quotation.updated_at.desc())
    )
    quotations = result.scalars().all()

    if not quotations:
        raise HTTPException(status_code=404, detail="No approved or moved quotations found")

    # Convert ORM objects to Pydantic models
    quotations_data = [
        QuotationDetailResponse.model_validate(q, from_attributes=True)
        for q in quotations
    ]

    return {"message": "Approved or moved quotations retrieved", "data": quotations_data}

# =====================================================
# 🔹 GET SALES ORDER BY ID
# =====================================================
async def get_sales_order_by_id(db: AsyncSession, order_id: int) -> SalesOrderResponse:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id).options(selectinload(SalesOrder.quotation))
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return SalesOrderResponse.model_validate(order, from_attributes=True)


# =====================================================
# 🔹 GET ALL SALES ORDERS
# =====================================================
async def get_all_sales_orders(db: AsyncSession) -> list[SalesOrderResponse]:
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.quotation)).order_by(SalesOrder.created_at.desc())
    )
    orders = result.scalars().all()
    if not orders:
        raise HTTPException(status_code=404, detail="No sales orders found")
    return [SalesOrderResponse.model_validate(o, from_attributes=True) for o in orders]

# =====================================================
# 🔹 RETRIEVAL SERVICES WITH PROPER HTTP CODES
# =====================================================

async def get_sales_orders_by_customer(db: AsyncSession, customer_id: int):
    """
    Fetch all Sales Orders for a specific customer, ordered by creation date.
    Raises 404 if no orders found.
    """
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.quotation))
        .where(SalesOrder.customer_id == customer_id)
        .order_by(SalesOrder.created_at.desc())
    )
    orders = result.scalars().all()

    if not orders:
        raise HTTPException(
            status_code=404,
            detail=f"No sales orders found for customer ID {customer_id}"
        )

    return orders


async def get_work_status_by_order_id(db: AsyncSession, order_id: int):
    """
    Fetch a Sales Order by ID and include its quotation and work status.
    Raises 404 if the order does not exist.
    """
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.quotation))
        .where(SalesOrder.id == order_id)
    )
    order = result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Work status not found for order ID {order_id}"
        )

    return order
