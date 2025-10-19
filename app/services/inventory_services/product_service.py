# app/services/product_service.py
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.models.inventory_models import Product
from app.schemas.inventory_schemas import ProductCreate, ProductUpdate, ProductOut
from app.utils.activity_helpers import log_user_activity


# ---------------------------------------------------
# CREATE PRODUCT
# ---------------------------------------------------
async def create_product(db: AsyncSession, data: ProductCreate, current_user):
    """
    Create a new product and log the creation in the activity log.
    """
    try:
        existing = await db.execute(
            select(Product).where(Product.name == data.name, Product.is_deleted == False)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail=f"Product '{data.name}' already exists")

        product = Product(**data.model_dump())
        db.add(product)
        await db.flush()  # ensures product.id is available

        # ✅ Log creation
        if current_user:
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} created product '{product.name}' (ID: {product.id})"
            )

        await db.commit()
        await db.refresh(product)
        return {"message": "Product created successfully", "data": ProductOut.model_validate(product)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating product: {e}")


# ---------------------------------------------------
# GET ALL PRODUCTS
# ---------------------------------------------------
async def get_all_products(db: AsyncSession) -> dict:
    """
    Fetch all non-deleted products.
    """
    result = await db.execute(select(Product).where(Product.is_deleted == False))
    products = result.scalars().all()
    return {
        "message": "Products fetched successfully",
        "data": [ProductOut.model_validate(p) for p in products],
    }


# ---------------------------------------------------
# GET SINGLE PRODUCT
# ---------------------------------------------------
async def get_product(db: AsyncSession, product_id: int) -> dict:
    """
    Fetch product by ID.
    """
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product fetched successfully", "data": ProductOut.model_validate(product)}


# ---------------------------------------------------
# UPDATE PRODUCT
# ---------------------------------------------------
async def update_product(db: AsyncSession, product_id: int, data: ProductUpdate, current_user):
    """
    Update product details and log the changes.
    """
    try:
        result = await db.execute(
            select(Product).where(Product.id == product_id, Product.is_deleted == False)
        )
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Validate fields
        if data.price is not None and data.price < 0:
            raise HTTPException(status_code=400, detail="Price must be non-negative")
        if data.quantity_showroom is not None and data.quantity_showroom < 0:
            raise HTTPException(status_code=400, detail="Showroom quantity must be non-negative")
        if data.quantity_warehouse is not None and data.quantity_warehouse < 0:
            raise HTTPException(status_code=400, detail="Warehouse quantity must be non-negative")

        # Track changes
        changes = []

        if data.name and data.name != product.name:
            existing = await db.execute(
                select(Product).where(
                    Product.name == data.name,
                    Product.id != product_id,
                    Product.is_deleted == False,
                )
            )
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail=f"Product '{data.name}' already exists")
            changes.append(f"name: {product.name} → {data.name}")
            product.name = data.name

        # Update remaining fields
        for key, value in data.model_dump(exclude_unset=True).items():
            if key != "name":
                old_val = getattr(product, key)
                if old_val != value:
                    changes.append(f"{key}: {old_val} → {value}")
                    setattr(product, key, value)

        db.add(product)
        await db.refresh(product)

        # ✅ Log changes
        if current_user and changes:
            change_summary = ", ".join(changes)
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} updated product '{product.name}' "
                        f"(ID: {product.id}) — {change_summary}"
            )
            await db.commit()

        return {"message": "Product updated successfully", "data": ProductOut.model_validate(product)}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating product: {e}")


# ---------------------------------------------------
# DELETE PRODUCT (Soft Delete)
# ---------------------------------------------------
async def delete_product(db: AsyncSession, product_id: int, current_user):
    """
    Soft delete a product and log the deletion.
    """
    try:
        result = await db.execute(
            select(Product).where(Product.id == product_id, Product.is_deleted == False)
        )
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.is_deleted = True
        db.add(product)

        # ✅ Log deletion
        if current_user:
            await log_user_activity(
                db,
                user_id=current_user.id,
                username=current_user.username,
                message=f"{current_user.role.capitalize()} deleted product '{product.name}' (ID: {product.id})"
            )
            await db.commit()

        return {"message": "Product deleted successfully"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting product: {e}")


