from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.inventory_services.supplier_service import create_supplier, get_all_suppliers, get_supplier, update_supplier, delete_supplier
from app.schemas.inventory_schemas import SupplierCreate, SupplierUpdate, SupplierCreateResponse, SupplierListResponse, MessageResponse
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/suppliers", tags=["Suppliers CRUD"])

@router.post("", response_model=SupplierCreateResponse)
@require_role(["admin", "inventory"])
async def create_supplier_route(data: SupplierCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await create_supplier(db, data)

@router.get("", response_model=SupplierListResponse)
@require_role(["admin", "inventory"])
async def list_suppliers(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_all_suppliers(db)

@router.get("/{supplier_id}", response_model=SupplierCreateResponse)
@require_role(["admin", "inventory"])
async def get_supplier_by_id(supplier_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_supplier(db, supplier_id)

@router.put("/{supplier_id}", response_model=SupplierCreateResponse)
@require_role(["admin", "inventory"])
async def update_supplier_route(supplier_id: int, data: SupplierUpdate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await update_supplier(db, supplier_id, data)

@router.delete("/{supplier_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_supplier_route(supplier_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await delete_supplier(db, supplier_id)
