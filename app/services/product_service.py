from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.models.inventory_models import Product
from app.schemas.inventory_schemas import ProductCreate, ProductUpdate, ProductOut, StockAlert

# --------------------------
# Product Services
# --------------------------
async def create_product(db: AsyncSession, data: ProductCreate, created_by: str) -> dict:
    existing = await db.execute(select(Product).where(Product.name == data.name, Product.is_deleted == False))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Product '{data.name}' already exists")
    
    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {"message": "Product created successfully", "data": ProductOut.model_validate(product)}

async def get_all_products(db: AsyncSession) -> dict:
    result = await db.execute(select(Product).where(Product.is_deleted == False))
    products = result.scalars().all()
    return {"message": "Products fetched successfully", "data": [ProductOut.model_validate(p) for p in products]}

async def get_product(db: AsyncSession, product_id: int) -> dict:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_deleted == False))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product fetched successfully", "data": ProductOut.model_validate(product)}

async def update_product(db: AsyncSession, product_id: int, data: ProductUpdate) -> dict:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_deleted == False))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.price is not None and data.price < 0:
        raise HTTPException(status_code=400, detail="Price must be non-negative")
    if data.quantity_showroom is not None and data.quantity_showroom < 0:
        raise HTTPException(status_code=400, detail="Showroom quantity must be non-negative")
    if data.quantity_warehouse is not None and data.quantity_warehouse < 0:
        raise HTTPException(status_code=400, detail="Warehouse quantity must be non-negative")

    if data.name and data.name != product.name:
        existing = await db.execute(
            select(Product).where(Product.name == data.name, Product.id != product_id, Product.is_deleted == False)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail=f"Product '{data.name}' already exists")
        product.name = data.name

    for key, value in data.model_dump(exclude_unset=True).items():
        if key != "name":
            setattr(product, key, value)

    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {"message": "Product updated successfully", "data": ProductOut.model_validate(product)}

async def delete_product(db: AsyncSession, product_id: int) -> dict:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.is_deleted == False))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_deleted = True
    db.add(product)
    await db.commit()
    return {"message": "Product deleted successfully"}

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
