from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.sales_order_schema import (
    SalesOrderResponse,
    SalesOrderStatusUpdate,
    QuotationDetailMessageResponse
)
from app.services.sales_order_service import (
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
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/billing/sales_orders", tags=["Sales Orders"])

# GET approved or moved quotations
@require_role(["admin", "cashier"])
@router.get("/quotations/status", response_model=QuotationDetailMessageResponse)
async def get_approved_moved_quotations(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_approved_or_moved_quotations(db, _user)

# GET all sales orders
@require_role(["admin", "cashier"])
@router.get("/", response_model=list[SalesOrderResponse])
async def get_all_orders(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_all_sales_orders(db, _user)

# GET sales order by ID
@require_role(["admin", "cashier"])
@router.get("/{order_id}", response_model=SalesOrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_sales_order_by_id(db, order_id, _user)

# GET sales orders by customer ID
@require_role(["admin", "cashier"])
@router.get("/customer/{customer_id}", response_model=list[SalesOrderResponse])
async def get_orders_by_customer(customer_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    orders = await get_sales_orders_by_customer(db, customer_id, _user)
    return orders

# GET work status by order ID
@require_role(["admin", "cashier", "inventory"])
@router.get("/{order_id}/status", response_model=SalesOrderResponse)
async def get_work_status(order_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    order = await get_work_status_by_order_id(db, order_id, _user)
    return order

# POST create from quotation
@require_role(["admin", "cashier"])
@router.post("/{quotation_id}", response_model=SalesOrderResponse, status_code=201)
async def create_order(quotation_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await create_sales_order_from_quotation(db, quotation_id, _user)

# POST approve order
@require_role(["admin"])
@router.post("/{order_id}/approve", response_model=SalesOrderResponse)
async def approve_order_route(order_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await approve_order(db, order_id, _user)

# PUT update work status
@require_role(["admin", "cashier", "inventory"])
@router.put("/{order_id}/status", response_model=SalesOrderResponse)
async def update_status(order_id: int, status_update: SalesOrderStatusUpdate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await update_work_status(db, order_id, status_update.status, status_update.note or "", _user)

# PUT mark complete
@require_role(["admin", "cashier"])
@router.put("/{order_id}/complete", response_model=SalesOrderResponse)
async def mark_complete(order_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await mark_sales_order_complete_service(db, order_id, _user)

# PUT move to invoice
@require_role(["admin", "cashier"])
@router.put("/{order_id}/move-to-invoice", response_model=SalesOrderResponse)
async def move_invoice(order_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await move_sales_order_to_invoice(db, order_id, _user)


