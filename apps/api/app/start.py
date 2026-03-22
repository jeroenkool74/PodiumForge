from __future__ import annotations

import os
import subprocess

import uvicorn

from app.seed import seed


TRUE_VALUES = {"1", "true", "yes", "on"}


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def main() -> None:
    if env_flag("RUN_MIGRATIONS", True):
        subprocess.run(["alembic", "upgrade", "head"], check=True)

    if env_flag("RUN_SEED", True):
        seed()

    uvicorn.run(
        "app.main:app",
        host=os.getenv("UVICORN_HOST", "0.0.0.0"),
        port=int(os.getenv("UVICORN_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
