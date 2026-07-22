"""platform subscription onboarding

Revision ID: 0002_platform_subscriptions
Revises: 0001_initial
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_platform_subscriptions"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tenant_status = postgresql.ENUM(
        "pending", "active", "suspended", "cancelled", name="tenant_status", create_type=False
    )
    subscription_status = postgresql.ENUM(
        "trial", "active", "past_due", "cancelled", name="subscription_status", create_type=False
    )
    request_status = postgresql.ENUM(
        "pending", "approved", "rejected", name="subscription_request_status", create_type=False
    )

    bind = op.get_bind()
    for enum_type in (tenant_status, subscription_status, request_status):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("owner_name", sa.String(120), nullable=False),
        sa.Column("owner_mobile", sa.String(15), nullable=False),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("parking_location", sa.String(255), nullable=True),
        sa.Column("status", tenant_status, nullable=False, server_default="active"),
        sa.Column("subscription_status", subscription_status, nullable=False, server_default="active"),
        sa.Column("plan_name", sa.String(80), nullable=False, server_default="manual"),
        sa.Column("database_name", sa.String(120), nullable=True),
        sa.Column("database_url", sa.Text(), nullable=True),
        sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_owner_mobile", "tenants", ["owner_mobile"])
    op.create_index("ix_tenants_status", "tenants", ["status"])
    op.create_index("ix_tenants_subscription_status", "tenants", ["subscription_status"])

    op.add_column("users", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_foreign_key("fk_users_tenant_id_tenants", "users", "tenants", ["tenant_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "subscription_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("parking_name", sa.String(150), nullable=False),
        sa.Column("owner_name", sa.String(120), nullable=False),
        sa.Column("owner_mobile", sa.String(15), nullable=False),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("parking_location", sa.String(255), nullable=True),
        sa.Column("expected_trucks_per_day", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", request_status, nullable=False, server_default="pending"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_subscription_requests_owner_mobile", "subscription_requests", ["owner_mobile"])
    op.create_index("ix_subscription_requests_status", "subscription_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_subscription_requests_status", table_name="subscription_requests")
    op.drop_index("ix_subscription_requests_owner_mobile", table_name="subscription_requests")
    op.drop_table("subscription_requests")

    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")

    op.drop_index("ix_tenants_subscription_status", table_name="tenants")
    op.drop_index("ix_tenants_status", table_name="tenants")
    op.drop_index("ix_tenants_owner_mobile", table_name="tenants")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")

    bind = op.get_bind()
    for enum_name in ("subscription_request_status", "subscription_status", "tenant_status"):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
