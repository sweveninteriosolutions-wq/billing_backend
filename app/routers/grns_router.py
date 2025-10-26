# app/routers/grn_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.inventory_services.grn_service import create_grn, verify_grn, get_all_grns, delete_grn
from app.schemas.inventory_schemas import GRNCreate, GRNCreateResponse, GRNListResponse, MessageResponse
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/inventory/grns", tags=["GRNs CRUD"])

# ---------------------------
# CREATE GRN
# ---------------------------
@router.post("", response_model=GRNCreateResponse)
@require_role(["admin", "inventory"])
async def create_grn_route(grn: GRNCreate, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await create_grn(db, grn, current_user=_user)


# ---------------------------
# VERIFY GRN
# ---------------------------
@router.post("/{grn_id}/verify", response_model=GRNCreateResponse)
@require_role(["admin"])
async def verify_grn_route(grn_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await verify_grn(db, grn_id, current_user=_user)


# ---------------------------
# LIST ALL GRNs
# ---------------------------
@router.get("", response_model=GRNListResponse)
@require_role(["admin", "inventory"])
async def list_grns(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_all_grns(db)


# ---------------------------
# DELETE GRN
# ---------------------------
@router.delete("/{grn_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_grn_route(grn_id: int, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await delete_grn(db, grn_id, current_user=_user)
