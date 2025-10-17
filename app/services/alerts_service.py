from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.inventory_models import Product
from app.schemas.inventory_schemas import StockAlert
from typing import List

async def get_stock_alerts(db: AsyncSession) -> List[StockAlert]:
    result = await db.execute(select(Product).where(Product.is_deleted == False))
    products = result.scalars().all()
    alerts = []
    for p in products:
        if p.quantity_showroom < p.min_stock_threshold or (p.quantity_showroom + p.quantity_warehouse) < p.min_stock_threshold:
            alerts.append(
                StockAlert(
                    product_id=p.id,
                    product_name=p.name,
                    quantity_showroom=p.quantity_showroom,
                    quantity_total=p.quantity_showroom + p.quantity_warehouse,
                    min_stock_threshold=p.min_stock_threshold
                )
            )
    return alerts
