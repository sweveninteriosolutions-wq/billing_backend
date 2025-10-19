from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.billing_models.customer_models import Customer
from app.models.user_models import User  # Assuming User model exists
from app.schemas.billing_schemas.customer_schema import CustomerOut, CustomerResponse, CustomerListResponse

from sqlalchemy.orm import aliased

async def create_customer(db: AsyncSession, customer_data: CustomerCreate, user_id: int) -> CustomerResponse:
    try:
        # Create customer
        customer_dict = customer_data.dict()
        customer_dict["created_by"] = user_id
        customer_dict["updated_by"] = user_id
        customer = Customer(**customer_dict)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

        # Fetch again with User join to get names
        created_user = aliased(User)
        updated_user = aliased(User)
        stmt = (
            select(
                Customer,
                created_user.username.label("created_by_name"),
                updated_user.username.label("updated_by_name")
            )
            .outerjoin(created_user, Customer.created_by == created_user.id)
            .outerjoin(updated_user, Customer.updated_by == updated_user.id)
            .where(Customer.id == customer.id)
        )
        result = await db.execute(stmt)
        row = result.first()
        cust, created_by_name, updated_by_name = row

        cust_out = CustomerOut.from_orm(cust)
        cust_out.created_by_name = created_by_name
        cust_out.updated_by_name = updated_by_name

        return CustomerResponse(
            message="Customer created successfully",
            data=cust_out
        )

    except IntegrityError as e:
        await db.rollback()
        # Check if it's a unique constraint violation
        if "unique" in str(e.orig).lower() or "duplicate" in str(e.orig).lower():
            raise HTTPException(
                status_code=400,
                detail="Customer with this email already exists."
            )
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e.orig)}")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while creating the customer.")


# GET SINGLE CUSTOMER
async def get_customer(db: AsyncSession, customer_id: int) -> CustomerResponse:
    customer = await db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=404, detail="Customer not found")
    # Optional: fetch names for created_by / updated_by
    created_by_name = updated_by_name = None
    if customer.created_by:
        u = await db.get(User, customer.created_by)
        created_by_name = u.username if u else None
    if customer.updated_by:
        u = await db.get(User, customer.updated_by)
        updated_by_name = u.username if u else None
    cust_out = CustomerOut.from_orm(customer)
    cust_out.created_by_name = created_by_name
    cust_out.updated_by_name = updated_by_name
    return CustomerResponse(message="Customer retrieved successfully", data=cust_out)


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, asc, desc
from sqlalchemy.orm import aliased
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.billing_models.customer_models import Customer
from app.models.user_models import User
from app.schemas.billing_schemas.customer_schema import CustomerOut, CustomerResponse, CustomerListResponse

async def get_all_customers(
    db: AsyncSession,
    name: str = None,
    email: str = None,
    phone: str = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    order: str = "desc"
) -> CustomerListResponse:

    created_user = aliased(User)
    updated_user = aliased(User)

    # Base query with joins
    query = (
        select(
            Customer,
            created_user.username.label("created_by_name"),
            updated_user.username.label("updated_by_name")
        )
        .outerjoin(created_user, Customer.created_by == created_user.id)
        .outerjoin(updated_user, Customer.updated_by == updated_user.id)
        .where(Customer.is_active == True)
    )

    # Apply search filters
    if name:
        query = query.where(Customer.name.ilike(f"%{name}%"))
    if email:
        query = query.where(Customer.email.ilike(f"%{email}%"))
    if phone:
        query = query.where(Customer.phone.ilike(f"%{phone}%"))

    # Allowed sort fields
    sort_col_map = {
        "name": Customer.name,
        "created_at": Customer.created_at,
        "created_by_name": created_user.username,
        "updated_by_name": updated_user.username
    }

    # Safe fallback and warning
    warning = None
    if sort_by.lower() not in sort_col_map:
        warning = f"sort_by '{sort_by}' is invalid, defaulted to 'created_at'"
        sort_col = Customer.created_at
    else:
        sort_col = sort_col_map[sort_by.lower()]

    # Determine order
    sort_order = asc(sort_col) if order.lower() == "asc" else desc(sort_col)
    query = query.order_by(sort_order)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    customer_list = []
    for customer, created_by_name, updated_by_name in rows:
        cust_out = CustomerOut.from_orm(customer)
        cust_out.created_by_name = created_by_name
        cust_out.updated_by_name = updated_by_name
        customer_list.append(cust_out)

    return CustomerListResponse(
        message="Customers retrieved successfully",
        total=total,
        data=customer_list,
        warning=warning  # Include warning if any
    )

# UPDATE CUSTOMER
async def update_customer(db: AsyncSession, customer_id: int, data: dict, user_id: int) -> CustomerResponse:
    customer = await db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in data.items():
        setattr(customer, key, value)
    customer.updated_by = user_id
    await db.commit()

    # Reuse get_customer to return a consistent, fully populated object
    response = await get_customer(db, customer_id)
    response.message = "Customer updated successfully"
    return response


# SOFT DELETE CUSTOMER
async def delete_customer(db: AsyncSession, customer_id: int, user_id: int) -> CustomerResponse:
    # Get the full customer object before deletion to ensure a consistent response.
    response = await get_customer(db, customer_id)

    # Now, perform the soft delete.
    customer = await db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.is_active = False
    customer.updated_by = user_id
    await db.commit()

    response.message = "Customer deleted successfully"
    return response
