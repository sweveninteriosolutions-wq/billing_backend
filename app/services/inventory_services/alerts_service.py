from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.inventory_models import Product
from app.schemas.inventory_schemas import StockAlert
from typing import List
from sqlalchemy import or_

async def get_stock_alerts(db: AsyncSession) -> List[StockAlert]:
    alert_condition = or_(
        Product.quantity_showroom < Product.min_stock_threshold,
        (Product.quantity_showroom + Product.quantity_warehouse) < Product.min_stock_threshold
    )
    result = await db.execute(
        select(Product).where(Product.is_deleted == False, alert_condition)
    )
    products = result.scalars().all()
    return [
        StockAlert(
            product_id=p.id,
            product_name=p.name,
            quantity_showroom=p.quantity_showroom,
            quantity_total=p.quantity_showroom + p.quantity_warehouse,
            min_stock_threshold=p.min_stock_threshold
        )
        for p in products
    ]
