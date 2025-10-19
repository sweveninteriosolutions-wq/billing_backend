from fastapi import APIRouter
from .customers_router import router as customers_router
# from .quotations_router import router as quotations_router
# from .orders_router import router as orders_router
# from .invoices_router import router as invoices_router
# from .payments_router import router as payments_router
# from .loyalty_router import router as loyalty_router

router = APIRouter(prefix="/billing")

router.include_router(customers_router)
# router.include_router(quotations_router)
# router.include_router(orders_router)
# router.include_router(invoices_router)
# router.include_router(payments_router)
# router.include_router(loyalty_router)
