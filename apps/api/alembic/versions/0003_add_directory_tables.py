from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_directory_tables"
down_revision = "0002_user_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "player_directory_entries" not in existing_tables:
        op.create_table(
            "player_directory_entries",
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_player_directory_entries")),
            sa.UniqueConstraint("name", name=op.f("uq_player_directory_entries_name")),
        )
        op.create_index(
            op.f("ix_player_directory_entries_name"),
            "player_directory_entries",
            ["name"],
            unique=True,
        )

    if "team_directory_entries" not in existing_tables:
        op.create_table(
            "team_directory_entries",
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_team_directory_entries")),
            sa.UniqueConstraint("name", name=op.f("uq_team_directory_entries_name")),
        )
        op.create_index(
            op.f("ix_team_directory_entries_name"),
            "team_directory_entries",
            ["name"],
            unique=True,
        )

    if "team_directory_members" not in existing_tables:
        op.create_table(
            "team_directory_members",
            sa.Column("team_id", sa.String(length=36), nullable=False),
            sa.Column("player_id", sa.String(length=36), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["player_id"],
                ["player_directory_entries.id"],
                name=op.f(
                    "fk_team_directory_members_player_id_player_directory_entries"
                ),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["team_id"],
                ["team_directory_entries.id"],
                name=op.f("fk_team_directory_members_team_id_team_directory_entries"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_team_directory_members")),
            sa.UniqueConstraint(
                "team_id", "player_id", name="uq_team_directory_member"
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "team_directory_members" in existing_tables:
        op.drop_table("team_directory_members")
    if "team_directory_entries" in existing_tables:
        op.drop_index(
            op.f("ix_team_directory_entries_name"), table_name="team_directory_entries"
        )
        op.drop_table("team_directory_entries")
    if "player_directory_entries" in existing_tables:
        op.drop_index(
            op.f("ix_player_directory_entries_name"),
            table_name="player_directory_entries",
        )
        op.drop_table("player_directory_entries")
