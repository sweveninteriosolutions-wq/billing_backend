from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.schemas.complaint_schema import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintUpdate,
)
from app.services.complaint_service import (
    create_complaint,
    get_all_complaints,
    get_complaint_by_id,
    update_complaint,
    delete_complaint,
)
from app.core.db import get_db
from app.models.user_models import User
from app.utils.get_user import get_current_user
from app.models.complaint_models import ComplaintStatus, ComplaintPriority

router = APIRouter(prefix="/billing/complaints", tags=["Complaints"])


# 🧾 Create Complaint
@router.post("/", response_model=ComplaintResponse)
async def route_create_complaint(
    payload: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_complaint(db, payload, current_user)


# 📋 Get All Complaints (with filters & pagination)
@router.get("/", response_model=List[ComplaintResponse])
async def route_get_all_complaints(
    db: AsyncSession = Depends(get_db),
    status: Optional[ComplaintStatus] = Query(None, description="Filter by status"),
    priority: Optional[ComplaintPriority] = Query(None, description="Filter by priority"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    date_from: Optional[datetime] = Query(None, description="Filter by creation date (start)"),
    date_to: Optional[datetime] = Query(None, description="Filter by creation date (end)"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    limit: int = Query(25, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    return await get_all_complaints(
        db=db,
        status=status,
        priority=priority,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
    )


# 🔍 Get Complaint by ID
@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def route_get_complaint(complaint_id: int, db: AsyncSession = Depends(get_db)):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


# ✏️ Update Complaint
@router.put("/{complaint_id}", response_model=ComplaintResponse)
async def route_update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = await update_complaint(db, complaint_id, payload, current_user)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


# 🗑️ Soft Delete Complaint
@router.delete("/{complaint_id}", response_model=ComplaintResponse)
async def route_delete_complaint(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = await delete_complaint(db, complaint_id, current_user)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint
