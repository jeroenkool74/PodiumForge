from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.core.enums import RoleName
from app.core.security import get_password_hash
from app.main import create_app
from app.models import Role, User


@pytest.fixture()
def db_session(tmp_path: Path) -> Session:
    database_path = tmp_path / "podiumforge-test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    admin_role = Role(name=RoleName.ADMIN.value, description="admin")
    editor_role = Role(name=RoleName.TOURNAMENT_EDITOR.value, description="editor")
    session.add_all([admin_role, editor_role])
    session.flush()
    admin = User(
        username="admin",
        email="admin@podiumforge.local",
        password_hash=get_password_hash("admin1234"),
        roles=[admin_role, editor_role],
    )
    editor = User(
        username="editor",
        email="editor@podiumforge.local",
        password_hash=get_password_hash("editor1234"),
        roles=[editor_role],
    )
    session.add_all([admin, editor])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
