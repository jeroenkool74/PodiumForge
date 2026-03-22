from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User


def login(client: TestClient, login_value: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"login": login_value, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_user_management_requires_admin(client: TestClient) -> None:
    editor_token = login(client, "editor@podiumforge.local", "editor1234")
    forbidden = client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert forbidden.status_code == 403

    admin_token = login(client, "admin@podiumforge.local", "admin1234")
    allowed = client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert allowed.status_code == 200
    assert len(allowed.json()) == 2


def test_admin_can_create_user_and_see_it_in_follow_up_list(client: TestClient) -> None:
    admin_token = login(client, "admin@podiumforge.local", "admin1234")

    created = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "scorekeeper",
            "email": "scorekeeper@podiumforge.local",
            "password": "scorekeeper1234",
            "roles": ["TOURNAMENT_EDITOR"],
        },
    )
    assert created.status_code == 201

    follow_up = client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert follow_up.status_code == 200
    assert any(user["username"] == "scorekeeper" for user in follow_up.json())


def test_validation_errors_are_returned_as_readable_strings(client: TestClient) -> None:
    admin_token = login(client, "admin@podiumforge.local", "admin1234")

    response = client.post(
        "/api/v1/tournaments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": " ",
            "description": "demo",
            "format": "FFA_ELIMINATION",
            "participant_type": "PLAYER",
            "match_size": 5,
            "participants": [" ", "   "],
            "points_scheme": [],
            "advance_count": 2,
            "is_public": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Name: String should have at least 3 characters "
        "Participants: Value error, At least two participant names are required"
    )


def test_admin_can_change_password_and_delete_user(client: TestClient) -> None:
    admin_token = login(client, "admin@podiumforge.local", "admin1234")

    created = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "stageadmin",
            "email": "stageadmin@podiumforge.local",
            "password": "stageadmin1234",
            "roles": ["TOURNAMENT_EDITOR"],
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    changed = client.post(
        f"/api/v1/users/{user_id}/password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"password": "updatedpass1234"},
    )
    assert changed.status_code == 204

    updated_login = client.post(
        "/api/v1/auth/login",
        json={"login": "stageadmin@podiumforge.local", "password": "updatedpass1234"},
    )
    assert updated_login.status_code == 200

    deleted = client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deleted.status_code == 204

    follow_up = client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert follow_up.status_code == 200
    assert all(user["id"] != user_id for user in follow_up.json())

    deleted_login = client.post(
        "/api/v1/auth/login",
        json={"login": "stageadmin@podiumforge.local", "password": "updatedpass1234"},
    )
    assert deleted_login.status_code == 401


def test_admin_can_delete_tournament(client: TestClient) -> None:
    admin_token = login(client, "admin@podiumforge.local", "admin1234")

    created = client.post(
        "/api/v1/tournaments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Disposable Cup",
            "description": "demo",
            "format": "STANDALONE_MATCH",
            "participant_type": "PLAYER",
            "match_size": 2,
            "participants": ["Alpha", "Bravo"],
            "points_scheme": [],
            "is_public": True,
        },
    )
    assert created.status_code == 201
    tournament_id = created.json()["id"]

    deleted = client.delete(
        f"/api/v1/tournaments/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deleted.status_code == 204

    follow_up = client.get(
        f"/api/v1/tournaments/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert follow_up.status_code == 404


def test_tournament_editor_cannot_delete_tournament(client: TestClient) -> None:
    editor_token = login(client, "editor@podiumforge.local", "editor1234")
    forbidden = client.delete(
        "/api/v1/tournaments/tabletop-showcase",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert forbidden.status_code == 403


def test_password_reset_request_and_confirm_updates_login(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    captured: dict[str, str] = {}

    def fake_send_password_reset_email(
        recipient: str, username: str, reset_link: str, expires_at
    ) -> None:
        captured["recipient"] = recipient
        captured["username"] = username
        captured["reset_link"] = reset_link
        assert expires_at is not None

    monkeypatch.setattr(
        "app.services.password_reset_service.send_password_reset_email",
        fake_send_password_reset_email,
    )

    requested = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "editor@podiumforge.local"},
    )
    assert requested.status_code == 202
    assert requested.json()["message"] == (
        "If that email exists, a password reset link has been sent."
    )
    assert captured["recipient"] == "editor@podiumforge.local"
    assert captured["username"] == "editor"

    db_session.expire_all()
    editor = (
        db_session.query(User).filter(User.email == "editor@podiumforge.local").one()
    )
    assert editor.password_reset_token_hash is not None
    assert editor.password_reset_expires_at is not None

    token = parse_qs(urlparse(captured["reset_link"]).query)["token"][0]
    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "editorreset1234"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["message"] == (
        "Password updated. You can now sign in with your new password."
    )

    db_session.expire_all()
    updated_editor = (
        db_session.query(User).filter(User.email == "editor@podiumforge.local").one()
    )
    assert updated_editor.password_reset_token_hash is None
    assert updated_editor.password_reset_sent_at is None
    assert updated_editor.password_reset_expires_at is None

    updated_login = client.post(
        "/api/v1/auth/login",
        json={"login": "editor@podiumforge.local", "password": "editorreset1234"},
    )
    assert updated_login.status_code == 200


def test_password_reset_failure_clears_pending_token(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    def failing_send_password_reset_email(*_args, **_kwargs) -> None:
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr(
        "app.services.password_reset_service.send_password_reset_email",
        failing_send_password_reset_email,
    )

    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "editor@podiumforge.local"},
    )
    assert response.status_code == 503

    db_session.expire_all()
    editor = (
        db_session.query(User).filter(User.email == "editor@podiumforge.local").one()
    )
    assert editor.password_reset_token_hash is None
    assert editor.password_reset_sent_at is None
    assert editor.password_reset_expires_at is None
