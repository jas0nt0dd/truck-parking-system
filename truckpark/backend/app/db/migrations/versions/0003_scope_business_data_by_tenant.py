"""scope business data by tenant

Revision ID: 0003_tenant_scope
Revises: 0002_platform_subscriptions
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_tenant_scope"
down_revision: Union[str, None] = "0002_platform_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = (
    "trucks",
    "parking_sessions",
    "billing_rules",
    "payments",
    "notifications",
    "system_settings",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in TENANT_TABLES:
        columns = {column["name"] for column in inspector.get_columns(table)}
        index_names = {index["name"] for index in inspector.get_indexes(table)}
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys(table)}

        if "tenant_id" not in columns:
            op.add_column(table, sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
        if f"ix_{table}_tenant_id" not in index_names:
            op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        if f"fk_{table}_tenant_id_tenants" not in fk_names:
            op.create_foreign_key(
                f"fk_{table}_tenant_id_tenants",
                table,
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"fk_{table}_tenant_id_tenants", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
