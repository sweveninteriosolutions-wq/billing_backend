# --------------------------
# File: app/services/product_service.py
# Description: Service layer for Product CRUD operations and business logic
# --------------------------

from fastapi import HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, asc, desc, func, exists
from typing import List, Optional

from app.models.product_models import Product
from app.models.grn_models import GRN, GRNItem
from app.models.sales_order_models import SalesOrder
from app.models.invoice_models import Invoice
from app.schemas.product_schemas import ProductCreate, ProductUpdate, ProductOut
from app.utils.activity_helpers import log_user_activity

# --------------------------
# Allowed fields for sorting
# --------------------------
ALLOWED_SORT_FIELDS = ["id", "name", "category", "price", "created_at"]


# --------------------------
# CREATE PRODUCT
# --------------------------
async def create_product(db: AsyncSession, data: ProductCreate, current_user):
    """
    Create a new product and log the creation in the activity log.
    """
    try:
        # Check if product already exists
        existing = await db.execute(
            select(Product).where(Product.name == data.name, Product.is_deleted == False)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail=f"Product '{data.name}' already exists")

        # Create product
        product = Product(**data.model_dump())
        db.add(product)
        await db.flush()  # ensures product.id is available

        # Log creation
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


# --------------------------
# GET ALL PRODUCTS (with filters + pagination)
# --------------------------
async def get_all_products(
    db: AsyncSession,
    search: Optional[str] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    order: str = "desc",
) -> dict:
    """
    Fetch products with optional search, filtering, pagination, and sorting.
    """
    try:
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = "created_at"

        sort_order = desc(sort_by) if order.lower() == "desc" else asc(sort_by)

        # Base query
        stmt = select(Product).where(Product.is_deleted == False)
        count_stmt = select(func.count(Product.id)).where(Product.is_deleted == False)

        # Apply search filters
        if search:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%")
                )
            )
            count_stmt = count_stmt.where(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%")
                )
            )

        # Apply category filter
        if category:
            stmt = stmt.where(Product.category == category)
            count_stmt = count_stmt.where(Product.category == category)

        # Apply supplier filter
        if supplier_id:
            stmt = stmt.where(Product.supplier_id == supplier_id)
            count_stmt = count_stmt.where(Product.supplier_id == supplier_id)

        # Total count
        total = (await db.execute(count_stmt)).scalar() or 0

        # Pagination
        stmt = stmt.order_by(sort_order).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        products = result.scalars().all()

        return {
            "message": "Products fetched successfully",
            "total": total,
            "data": [ProductOut.model_validate(p) for p in products],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------
# GET SINGLE PRODUCT
# --------------------------
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


# --------------------------
# UPDATE PRODUCT
# --------------------------
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

        # Validate numeric fields
        if data.price is not None and data.price < 0:
            raise HTTPException(status_code=400, detail="Price must be non-negative")
        if data.quantity_showroom is not None and data.quantity_showroom < 0:
            raise HTTPException(status_code=400, detail="Showroom quantity must be non-negative")
        if data.quantity_warehouse is not None and data.quantity_warehouse < 0:
            raise HTTPException(status_code=400, detail="Warehouse quantity must be non-negative")

        # Track changes
        changes = []

        # Handle name change separately
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

        # Log changes
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


# --------------------------
# DELETE PRODUCT
# --------------------------
async def delete_product(db: AsyncSession, product_id: int, current_user):
    """
    Soft-delete product. Checks for linked GRNs, orders, and invoices before deletion.
    """
    # Fetch product
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if product exists in any verified GRN
    grn_exists = await db.scalar(
        select(exists().where(
            GRNItem.product_id == product_id,
            GRNItem.grn_id == GRN.id,
            GRN.status == "completed"
        ))
    )

    if grn_exists:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete product '{product.name}' (ID: {product.id}) — it is linked to a verified GRN."
        )

    # Optional: Check if product exists in any active SalesOrder or Invoice
    sales_order_exists = await db.scalar(
        select(exists().where(SalesOrder.quotation_snapshot["items"].contains([{"product_id": product_id}])) )
    )
    invoice_exists = await db.scalar(
        select(exists().where(Invoice.quotation_id.isnot(None)))  # depends on schema
    )

    if sales_order_exists or invoice_exists:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete product '{product.name}' (ID: {product.id}) — it is linked to an order or invoice."
        )

    # Soft delete
    product.is_deleted = True
    db.add(product)

    # Log user action
    if current_user:
        await log_user_activity(
            db,
            user_id=current_user.id,
            username=current_user.username,
            message=f"{current_user.role.capitalize()} deleted product '{product.name}' (ID: {product.id})"
        )

    await db.commit()

    return {"message": f"Product '{product.name}' deleted successfully"}
