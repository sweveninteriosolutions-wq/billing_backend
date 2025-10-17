from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.db import get_db
from app.services.inventory_services.alerts_service import get_stock_alerts

from app.schemas.inventory_schemas import StockAlert
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/alerts", tags=["Inventory Stock Alerts"])

@router.get("/inventory", response_model=List[StockAlert])
@require_role(["admin", "inventory"])
async def stock_alerts(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    return await get_stock_alerts(db)
