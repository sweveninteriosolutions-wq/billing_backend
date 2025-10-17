from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.stock_transfer_service import create_stock_transfer, complete_stock_transfer, get_stock_transfer, update_stock_transfer, delete_stock_transfer
from app.schemas.inventory_schemas import TransferCreate, TransferResponse, TransferUpdate, MessageResponse
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/transfers", tags=["Stock Transfers"])

@router.post("", response_model=TransferResponse)
@require_role(["admin", "inventory"])
async def create_transfer_route(transfer: TransferCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await create_stock_transfer(db, transfer, transferred_by=user.username)

@router.post("/{transfer_id}/complete", response_model=TransferResponse)
@require_role(["admin", "inventory"])
async def complete_transfer_route(transfer_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await complete_stock_transfer(db, transfer_id, completed_by=user.username)

@router.get("/{transfer_id}", response_model=TransferResponse)
@require_role(["admin", "inventory"])
async def get_transfer_by_id(transfer_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await get_stock_transfer(db, transfer_id)

@router.put("/{transfer_id}", response_model=TransferResponse)
@require_role(["admin", "inventory"])
async def update_transfer_route(transfer_id: int, data: TransferUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await update_stock_transfer(db, transfer_id, data)

@router.delete("/{transfer_id}", response_model=MessageResponse)
@require_role(["admin"])
async def delete_transfer_route(transfer_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await delete_stock_transfer(db, transfer_id)
