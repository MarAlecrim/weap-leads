from fastapi import APIRouter

from app.api.routes import conversas, funil, leads, login, painel, private, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(leads.router)
api_router.include_router(funil.router)
api_router.include_router(painel.router)
api_router.include_router(conversas.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
