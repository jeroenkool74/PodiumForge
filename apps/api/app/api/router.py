from __future__ import annotations

from fastapi import APIRouter

from app.modules.directory.router import router as directory_router
from app.modules.auth.router import router as auth_router
from app.modules.matches.router import router as matches_router
from app.modules.public.router import router as public_router
from app.modules.standings.router import router as standings_router
from app.modules.tournaments.router import router as tournaments_router
from app.modules.users.router import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(public_router)
api_router.include_router(auth_router)
api_router.include_router(directory_router)
api_router.include_router(users_router)
api_router.include_router(tournaments_router)
api_router.include_router(matches_router)
api_router.include_router(standings_router)
