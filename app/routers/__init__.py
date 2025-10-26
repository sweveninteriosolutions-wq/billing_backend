# app/routers/__init__.py

from .activity_router import router as activity_router
from .alerts_router import router as alerts_router
from .auth_router import router as auth_router
from .complaint_router import router as complaint_router
from .customers_router import router as customers_router
from .grns_router import router as grns_router
from .invoice_router import router as invoice_router
from .loyality_router import router as loyality_router
from .payments_router import router as payments_router
from .products_router import router as products_router
from .quotations_router import router as quotations_router
from .sales_orders_router import router as sales_orders_router
from .suppliers_router import router as suppliers_router
from .transfers_router import router as transfers_router
from .users_router import router as users_router

__all__ = [
    "activity_router",
    "alerts_router",
    "auth_router",
    "complaint_router",
    "customers_router",
    "grns_router",
    "invoice_router",
    "loyality_router",
    "payments_router",
    "products_router",
    "quotations_router",
    "sales_orders_router",
    "suppliers_router",
    "transfers_router",
    "users_router",
]
