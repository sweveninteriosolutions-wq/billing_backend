# app/router/supplier_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.db import get_db
from app.services.supplier_service import (
    create_supplier,
    get_all_suppliers,
    get_supplier,
    update_supplier,
    delete_supplier,
    get_supplier_grns,
    get_supplier_products
)
from app.schemas.supplier_schemas import (
    SupplierCreate,
    SupplierUpdate,
    SupplierCreateResponse,
    SupplierListResponse,
    MessageResponse,
    GRNResponseList,
    ProductListResponse

)
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/suppliers", tags=["Suppliers CRUD"])


# -----------------------------------------------------------
# CREATE SUPPLIER
# -----------------------------------------------------------
@router.post("", response_model=SupplierCreateResponse)
@require_role(["admin", "inventory"])
async def create_supplier_route(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await create_supplier(db, data, _user)


# -----------------------------------------------------------
# LIST ALL SUPPLIERS (with pagination, filters)
# -----------------------------------------------------------
@router.get("", response_model=SupplierListResponse)
@require_role(["admin", "inventory"])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search by supplier name or contact person"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    return await get_all_suppliers(db, search, page, page_size, sort_by, order)


# -----------------------------------------------------------
# GET SUPPLIER BY ID
# -----------------------------------------------------------
@router.get("/{supplier_id}", response_model=SupplierCreateResponse)
@require_role(["admin", "inventory"])
async def get_supplier_by_id(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await get_supplier(db, supplier_id)


# -----------------------------------------------------------
# UPDATE SUPPLIER
# -----------------------------------------------------------
@router.put("/{supplier_id}", response_model=SupplierCreateResponse)
@require_role(["admin", "inventory"])
async def update_supplier_route(
    supplier_id: int,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await update_supplier(db, supplier_id, data, _user)


# -----------------------------------------------------------
# DELETE SUPPLIER
# -----------------------------------------------------------
@router.delete("/{supplier_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_supplier_route(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await delete_supplier(db, supplier_id, _user)

# -----------------------------------------------------------
# GET SUPPLIER → GRNs
# -----------------------------------------------------------
@router.get("/{supplier_id}/grns", response_model=GRNResponseList)
@require_role(["admin", "inventory"])
async def get_supplier_grns_route(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Get all GRNs linked to a supplier.
    """
    return await get_supplier_grns(db, supplier_id)


# -----------------------------------------------------------
# GET SUPPLIER → PRODUCTS
# -----------------------------------------------------------
@router.get("/{supplier_id}/products", response_model=ProductListResponse)
@require_role(["admin", "inventory"])
async def get_supplier_products_route(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Get all products linked to a supplier.
    """
    return await get_supplier_products(db, supplier_id)