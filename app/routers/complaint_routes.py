# app/routes/billing_routes/complaint_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.schemas.complaint_schema import ComplaintCreate, ComplaintResponse, ComplaintUpdate
from app.services.complaint_service import (
    create_complaint, get_all_complaints, get_complaint_by_id, update_complaint, delete_complaint
)
from app.core.db import get_db
from app.models.user_models import User
from app.utils.get_user import get_current_user

router = APIRouter(prefix="/billing", tags=["Complaints"])

@router.post("/complaints", response_model=ComplaintResponse)
async def route_create_complaint(
    payload: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # from your auth dependency
):
    return await create_complaint(db, payload, current_user)

@router.get("/complaints", response_model=List[ComplaintResponse])
async def route_get_all_complaints(db: AsyncSession = Depends(get_db), ):
    return await get_all_complaints(db)

@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def route_get_complaint(complaint_id: int, db: AsyncSession = Depends(get_db)):
    complaint = await get_complaint_by_id(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.put("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def route_update_complaint(complaint_id: int, payload: ComplaintUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    complaint = await update_complaint(db, complaint_id, payload, current_user)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.delete("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def route_delete_complaint(complaint_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    complaint = await delete_complaint(db, complaint_id, current_user)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint
