from fastapi import APIRouter

from .products import router as products_router
from .suppliers import router as suppliers_router
from .grns import router as grns_router
from .transfers import router as transfers_router
from .alerts import router as alerts_router

router = APIRouter(prefix="/inventory")

router.include_router(products_router)
router.include_router(suppliers_router)
router.include_router(grns_router)
router.include_router(transfers_router)
router.include_router(alerts_router)
