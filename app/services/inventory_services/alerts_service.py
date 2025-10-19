from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from typing import List

from app.models.inventory_models import Product
from app.schemas.inventory_schemas import StockAlert
from app.utils.activity_helpers import log_user_activity


async def get_stock_alerts(db: AsyncSession, current_user = None) -> List[StockAlert]:
    """
    Fetch products that are below minimum stock thresholds.
    Only considers active products (is_deleted=False).
    Optionally logs the alert check by the current user.
    """
    try:
        alert_condition = or_(
            Product.quantity_showroom < Product.min_stock_threshold,
            (Product.quantity_showroom + Product.quantity_warehouse) < Product.min_stock_threshold
        )

        result = await db.execute(
            select(Product).where(Product.is_deleted == False, alert_condition)
        )
        products = result.scalars().all()

        # Log activity
        if current_user and products:
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} checked stock alerts ({len(products)} products below threshold)"
            )
            await db.commit()

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock alerts: {e}")
