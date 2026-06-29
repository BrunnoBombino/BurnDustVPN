from .user import user_router
from .admin import admin_router
from .payment import payment_router
from .registration import reg_router

# Это список, который мы будем подключать в main.py
routers = [user_router, admin_router, payment_router, reg_router]