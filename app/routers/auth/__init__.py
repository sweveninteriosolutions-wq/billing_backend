from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .activity_router import router as activity_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(activity_router)

