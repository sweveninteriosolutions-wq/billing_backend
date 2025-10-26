# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    activity_router, alerts_router, auth_router, complaint_router, customers_router,
    grns_router, invoice_router, loyality_router, payments_router, products_router,
    quotations_router, sales_orders_router, suppliers_router, transfers_router, users_router
)
from app.core.db import Base, engine, init_models
from app.middleware.activity_logger import ActivityLoggerMiddleware

app = FastAPI(
    title="Backend Billing API",
    description="FastAPI + Supabase backend for Billing & Inventory",
    version="0.1.0"
)
# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ActivityLoggerMiddleware)

# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

# Register routers
app.include_router(activity_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(complaint_router)
app.include_router(customers_router)
app.include_router(grns_router)
app.include_router(invoice_router)
app.include_router(loyality_router)
app.include_router(payments_router)
app.include_router(products_router)
app.include_router(quotations_router)
app.include_router(sales_orders_router)
app.include_router(suppliers_router)
app.include_router(transfers_router)
app.include_router(users_router)

#added


@app.on_event("startup")
async def on_startup():
    await init_models()
