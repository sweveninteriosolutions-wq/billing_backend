from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.db import get_db
from app.services.alerts_service import get_stock_alerts
from app.schemas.alert_schemas import StockAlert, StockAlertListResponse
from app.utils.get_user import get_current_user
from app.utils.check_roles import require_role

router = APIRouter(prefix="/alerts", tags=["Inventory Stock Alerts"])

@router.get("/inventory", response_model=StockAlertListResponse)
@require_role(["admin", "inventory"])
async def stock_alerts(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    Fetch all products below minimum stock thresholds.
    Only active (non-deleted) products are considered.
    Supports pagination and user activity logging.
    """
    data = await get_stock_alerts(db, current_user=_user, page=page, page_size=page_size)
    return {
        "message": f"{len(data)} products below stock threshold" if data else "All stocks are above threshold",
        "data": data
    }