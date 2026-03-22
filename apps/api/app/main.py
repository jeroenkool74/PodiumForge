from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="PodiumForge API",
        version="0.1.0",
        description="Local-first tournament management API with merged v1 and v2 features.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages: list[str] = []
        for error in exc.errors():
            location = [str(item) for item in error.get("loc", []) if item != "body"]
            field_name = " ".join(location).replace("_", " ").strip().title()
            message = error.get("msg", "Invalid value")
            messages.append(f"{field_name}: {message}" if field_name else message)

        return JSONResponse(
            status_code=422,
            content={"detail": " ".join(messages) if messages else "Validation failed"},
        )

    application.include_router(api_router)
    return application


app = create_app()
