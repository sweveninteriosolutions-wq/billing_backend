from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.billing_schemas.customer_schema import (
    CustomerCreate, CustomerUpdate,
    CustomerResponse, CustomerListResponse
)
from app.services.billing_services import customer_service
from app.core.db import get_db
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/customers", tags=["Customers"])

# CREATE
@router.post("/", response_model=CustomerResponse)
@require_role(["admin", "sales", "cashier"])
async def create_customer_route(
    customer: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await customer_service.create_customer(db, customer, _user.id)


# GET SINGLE
@router.get("/{customer_id}", response_model=CustomerResponse)
@require_role(["admin", "sales", "cashier"])
async def get_customer_route(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await customer_service.get_customer(db, customer_id)


# GET ALL WITH SEARCH, PAGINATION, SORTING
@router.get("/", response_model=CustomerListResponse)
@require_role(["admin", "sales", "cashier"])
async def list_customers_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    name: str = Query(None, description="Filter by name"),
    email: str = Query(None, description="Filter by email"),
    phone: str = Query(None, description="Filter by phone"),
    limit: int = Query(50, ge=1, le=100, description="Limit number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("created_at", description="Sort by field: name, created_at, created_by_name, updated_by_name"),
    order: str = Query("desc", description="Order: asc or desc")
):
    return await customer_service.get_all_customers(db, name, email, phone, limit, offset, sort_by, order)


# UPDATE
@router.put("/{customer_id}", response_model=CustomerResponse)
@require_role(["admin"])
async def update_customer_route(
    customer_id: int,
    customer: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await customer_service.update_customer(db, customer_id, customer.dict(exclude_unset=True), _user.id)


# SOFT DELETE
@router.delete("/{customer_id}", response_model=CustomerResponse)
@require_role(["admin"])
async def delete_customer_route(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user)
):
    return await customer_service.delete_customer(db, customer_id, _user.id)
