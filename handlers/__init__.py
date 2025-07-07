from .common import common_router
from .order_handlers import order_router

# Объединяем роутеры в один список для удобной регистрации в main.py
routers_list = [
    common_router,
    order_router,
]

__all__ = [
    "routers_list",
]
