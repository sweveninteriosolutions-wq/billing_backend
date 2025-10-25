from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.billing_schemas.sales_order_schema import (
    SalesOrderResponse,
    SalesOrderStatusUpdate,
    QuotationDetailMessageResponse
)
from app.services.billing_services.sales_order_service import (
    create_sales_order_from_quotation,
    approve_order,
    update_work_status,
    mark_sales_order_complete_service,
    move_sales_order_to_invoice,
    get_sales_order_by_id,
    get_all_sales_orders,
    get_approved_or_moved_quotations,
    get_sales_orders_by_customer,
    get_work_status_by_order_id
)

router = APIRouter(prefix="/sales_orders", tags=["Sales Orders"])

# GET approved or moved quotations
@router.get("/quotations/status", response_model=QuotationDetailMessageResponse)
async def get_approved_moved_quotations(db: AsyncSession = Depends(get_db)):
    return await get_approved_or_moved_quotations(db)

# GET all sales orders
@router.get("/", response_model=list[SalesOrderResponse])
async def get_all_orders(db: AsyncSession = Depends(get_db)):
    return await get_all_sales_orders(db)

# GET sales order by ID
@router.get("/{order_id}", response_model=SalesOrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    return await get_sales_order_by_id(db, order_id)

# GET sales orders by customer ID
@router.get("/customer/{customer_id}", response_model=list[SalesOrderResponse])
async def get_orders_by_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    orders = await get_sales_orders_by_customer(db, customer_id)
    if not orders:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No sales orders found for customer ID {customer_id}")
    return orders

# GET work status by order ID
@router.get("/{order_id}/status", response_model=SalesOrderResponse)
async def get_work_status(order_id: int, db: AsyncSession = Depends(get_db)):
    order = await get_work_status_by_order_id(db, order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Work status not found for order ID {order_id}")
    return order

# POST create from quotation
@router.post("/{quotation_id}", response_model=SalesOrderResponse, status_code=201)
async def create_order(quotation_id: int, db: AsyncSession = Depends(get_db)):
    return await create_sales_order_from_quotation(db, quotation_id)

# POST approve order
@router.post("/{order_id}/approve", response_model=SalesOrderResponse)
async def approve_order_route(order_id: int, db: AsyncSession = Depends(get_db)):
    return await approve_order(db, order_id)

# PUT update work status
@router.put("/{order_id}/status", response_model=SalesOrderResponse)
async def update_status(order_id: int, status_update: SalesOrderStatusUpdate, db: AsyncSession = Depends(get_db)):
    return await update_work_status(db, order_id, status_update.status, status_update.note or "")

# PUT mark complete
@router.put("/{order_id}/complete", response_model=SalesOrderResponse)
async def mark_complete(order_id: int, db: AsyncSession = Depends(get_db)):
    return await mark_sales_order_complete_service(db, order_id)

# PUT move to invoice
@router.put("/{order_id}/move-to-invoice", response_model=SalesOrderResponse)
async def move_invoice(order_id: int, db: AsyncSession = Depends(get_db)):
    return await move_sales_order_to_invoice(db, order_id)


