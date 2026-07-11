"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    user_role = postgresql.ENUM("admin", "gatekeeper", name="user_role", create_type=False)
    session_status = postgresql.ENUM("inside", "exited", name="session_status", create_type=False)
    payment_mode = postgresql.ENUM("cash", "upi", "credit", name="payment_mode", create_type=False)
    payment_status = postgresql.ENUM("paid", "pending", "credit", name="payment_status", create_type=False)
    notification_channel = postgresql.ENUM("whatsapp", name="notification_channel", create_type=False)
    notification_type = postgresql.ENUM("entry", "exit", name="notification_type", create_type=False)
    notification_status = postgresql.ENUM("pending", "sent", "failed", name="notification_status", create_type=False)

    bind = op.get_bind()
    for enum_type in (
        user_role, session_status, payment_mode, payment_status,
        notification_channel, notification_type, notification_status,
    ):
        enum_type.create(bind, checkfirst=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("mobile", sa.String(15), nullable=False, unique=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_root", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("must_reset_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_mobile", "users", ["mobile"])

    # --- trucks ---
    op.create_table(
        "trucks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("truck_number", sa.String(20), nullable=False),
        sa.Column("driver_name", sa.String(120), nullable=True),
        sa.Column("driver_mobile", sa.String(15), nullable=False),
        sa.Column("transport_company", sa.String(150), nullable=True),
        sa.Column("vehicle_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trucks_truck_number", "trucks", ["truck_number"])
    op.create_index("ix_trucks_driver_mobile", "trucks", ["driver_mobile"])

    # --- parking_sessions ---
    op.create_table(
        "parking_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("truck_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trucks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_photo_url", sa.String(500), nullable=True),
        sa.Column("exit_photo_url", sa.String(500), nullable=True),
        sa.Column("status", session_status, nullable=False, server_default="inside"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("gatekeeper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exit_gatekeeper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_parking_sessions_truck_id", "parking_sessions", ["truck_id"])
    op.create_index("ix_parking_sessions_status", "parking_sessions", ["status"])
    op.create_index("ix_parking_sessions_entry_time", "parking_sessions", ["entry_time"])

    # --- billing_rules ---
    op.create_table(
        "billing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_name", sa.String(120), nullable=False),
        sa.Column("from_hours", sa.Numeric(10, 2), nullable=False),
        sa.Column("to_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("charge", sa.Numeric(10, 2), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parking_sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_mode", payment_mode, nullable=True),
        sa.Column("payment_status", payment_status, nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gatekeeper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("billing_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_session_id", "payments", ["session_id"])
    op.create_index("ix_payments_payment_status", "payments", ["payment_status"])

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parking_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("mobile", sa.String(15), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("message_type", notification_type, nullable=False),
        sa.Column("status", notification_status, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_session_id", "notifications", ["session_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])

    # --- system_settings ---
    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("parking_name", sa.String(150), nullable=True),
        sa.Column("company_details", postgresql.JSONB(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("msg91_authkey", sa.String(255), nullable=True),
        sa.Column("msg91_sender_id", sa.String(50), nullable=True),
        sa.Column("msg91_whatsapp_number", sa.String(20), nullable=True),
        sa.Column("msg91_entry_template", sa.String(120), nullable=True),
        sa.Column("msg91_exit_template", sa.String(120), nullable=True),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("notifications")
    op.drop_table("payments")
    op.drop_table("billing_rules")
    op.drop_table("parking_sessions")
    op.drop_table("trucks")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in (
        "notification_status", "notification_type", "notification_channel",
        "payment_status", "payment_mode", "session_status", "user_role",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
