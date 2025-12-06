from .common import common_router
from .order_handlers import order_router
from .payment_handlers import payment_router
from .subscription_handlers import subscription_router

# Объединяем роутеры в один список для удобной регистрации в main.py
routers_list = [
    common_router,
    order_router,
    subscription_router,
    payment_router,
]

__all__ = [
    "routers_list",
]
