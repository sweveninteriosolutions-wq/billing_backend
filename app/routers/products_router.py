# app/routers/product_router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.db import get_db
from app.services.product_service import (
    create_product,
    get_all_products,
    get_product,
    update_product,
    delete_product,
)
from app.schemas.product_schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    MessageResponse,
)
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/products", tags=["Products CRUD"])

# -----------------------------------------------------------
# CREATE PRODUCT
# -----------------------------------------------------------
@router.post("", response_model=ProductResponse)
@require_role(["admin", "inventory"])
async def create_product_route(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Create a new product. Restricted to admin and inventory roles.
    """
    return await create_product(db, data, _user)


# -----------------------------------------------------------
# LIST ALL PRODUCTS
# -----------------------------------------------------------
@router.get("", response_model=ProductListResponse)
@require_role(["admin", "inventory"])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    """
    List products with optional search, filters, pagination, and sorting.
    """
    return await get_all_products(
        db, search, category, supplier_id, page, page_size, sort_by, order
    )


# -----------------------------------------------------------
# GET PRODUCT BY ID
# -----------------------------------------------------------
@router.get("/{product_id}", response_model=ProductResponse)
@require_role(["admin", "inventory"])
async def get_product_by_id(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Retrieve a single product by ID. Restricted to admin and inventory roles.
    """
    return await get_product(db, product_id)


# -----------------------------------------------------------
# UPDATE PRODUCT
# -----------------------------------------------------------
@router.put("/{product_id}", response_model=ProductResponse)
@require_role(["admin", "inventory"])
async def update_product_route(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Update an existing product. Restricted to admin and inventory roles.
    """
    return await update_product(db, product_id, data, _user)


# -----------------------------------------------------------
# DELETE PRODUCT
# -----------------------------------------------------------
@router.delete("/{product_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_product_route(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Soft-delete a product. Restricted to admin role only.
    """
    return await delete_product(db, product_id, _user)
