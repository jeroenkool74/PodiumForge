from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_user_password_reset"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "password_reset_token_hash" not in columns:
        op.add_column(
            "users",
            sa.Column("password_reset_token_hash", sa.String(length=64), nullable=True),
        )
    if "password_reset_sent_at" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "password_reset_sent_at", sa.DateTime(timezone=True), nullable=True
            ),
        )
    if "password_reset_expires_at" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "password_reset_expires_at", sa.DateTime(timezone=True), nullable=True
            ),
        )

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    index_name = op.f("ix_users_password_reset_token_hash")
    if index_name not in indexes:
        op.create_index(
            index_name,
            "users",
            ["password_reset_token_hash"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    index_name = op.f("ix_users_password_reset_token_hash")

    if index_name in indexes:
        op.drop_index(index_name, table_name="users")
    if "password_reset_expires_at" in columns:
        op.drop_column("users", "password_reset_expires_at")
    if "password_reset_sent_at" in columns:
        op.drop_column("users", "password_reset_sent_at")
    if "password_reset_token_hash" in columns:
        op.drop_column("users", "password_reset_token_hash")
