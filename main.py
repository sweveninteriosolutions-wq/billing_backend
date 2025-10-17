# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth
from temp import inventory_routes
from app.core.db import Base, engine, init_models
from app.routers.auth import users

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

# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(inventory_routes.router)

@app.on_event("startup")
async def on_startup():
    await init_models()

# Global exception handler (optional)
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return {"error": str(exc)}
