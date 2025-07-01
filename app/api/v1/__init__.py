from fastapi import APIRouter

from . import users_router
# Import other routers here as they are created
# e.g. from . import accounts_router
# e.g. from . import loans_router

api_v1_router = APIRouter()

api_v1_router.include_router(users_router.router, prefix="/users", tags=["Users"])
# api_v1_router.include_router(accounts_router.router, prefix="/accounts", tags=["Accounts"])
# api_v1_router.include_router(loans_router.router, prefix="/loans", tags=["Loans"])


__all__ = ["api_v1_router"]
