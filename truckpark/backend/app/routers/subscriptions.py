from __future__ import annotations

import re
import secrets
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_platform_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.billing_rule import BillingRule
from app.models.subscription_request import SubscriptionRequest, SubscriptionRequestStatus
from app.models.system_settings import SystemSettings
from app.models.tenant import SubscriptionStatus, Tenant, TenantStatus
from app.models.user import User, UserRole
from app.schemas.subscriptions import (
    SubscriptionApprovalOut,
    SubscriptionRequestCreate,
    SubscriptionRequestDecision,
    SubscriptionRequestOut,
    TenantOut,
)

router = APIRouter(tags=["subscriptions"])

DEFAULT_BILLING_RULES = [
    {"rule_name": "First 12 Hours", "from_hours": 0, "to_hours": 12, "charge": 100, "priority": 1},
    {"rule_name": "12-24 Hours", "from_hours": 12, "to_hours": 24, "charge": 150, "priority": 2},
    {"rule_name": "Additional Day", "from_hours": 24, "to_hours": None, "charge": 100, "priority": 3},
]


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _slug_base(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "tenant"


async def _unique_slug(db: AsyncSession, parking_name: str) -> str:
    base = _slug_base(parking_name)
    slug = base
    counter = 2
    while True:
        result = await db.execute(select(Tenant.id).where(Tenant.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base}-{counter}"
        counter += 1


@router.post(
    "/subscription-requests",
    response_model=SubscriptionRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription_request(
    payload: SubscriptionRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    active_request = await db.execute(
        select(SubscriptionRequest).where(
            SubscriptionRequest.owner_mobile == payload.owner_mobile,
            SubscriptionRequest.status == SubscriptionRequestStatus.pending,
        )
    )
    if active_request.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subscription request for this mobile number is already pending.",
        )

    request = SubscriptionRequest(**payload.model_dump())
    db.add(request)
    await db.flush()
    await db.refresh(request)
    return request


@router.get("/platform/subscription-requests", response_model=list[SubscriptionRequestOut])
async def list_subscription_requests(
    status_filter: SubscriptionRequestStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    query = select(SubscriptionRequest).order_by(SubscriptionRequest.requested_at.desc())
    if status_filter is not None:
        query = query.where(SubscriptionRequest.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/platform/tenants", response_model=list[TenantOut])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return result.scalars().all()


@router.post(
    "/platform/subscription-requests/{request_id}/approve",
    response_model=SubscriptionApprovalOut,
)
async def approve_subscription_request(
    request_id: uuid.UUID,
    payload: SubscriptionRequestDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    result = await db.execute(select(SubscriptionRequest).where(SubscriptionRequest.id == request_id))
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found")
    if request.status != SubscriptionRequestStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription request already reviewed")

    existing_user = await db.execute(select(User).where(User.mobile == request.owner_mobile))
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this owner mobile number already exists.",
        )

    now = datetime.now(timezone.utc)
    tenant = Tenant(
        name=request.parking_name,
        slug=await _unique_slug(db, request.parking_name),
        owner_name=request.owner_name,
        owner_mobile=request.owner_mobile,
        owner_email=request.owner_email,
        parking_location=request.parking_location,
        status=TenantStatus.active,
        subscription_status=SubscriptionStatus.active,
        plan_name=payload.plan_name or "manual",
        database_name=payload.database_name,
        database_url=payload.database_url,
        subscription_started_at=now,
        subscription_expires_at=payload.subscription_expires_at,
    )
    db.add(tenant)
    await db.flush()

    temporary_password = _generate_temp_password()
    owner = User(
        tenant_id=tenant.id,
        name=request.owner_name,
        mobile=request.owner_mobile,
        email=request.owner_email,
        role=UserRole.admin,
        password_hash=hash_password(temporary_password),
        is_active=True,
        is_root=True,
        must_reset_password=True,
    )
    db.add(owner)

    db.add(SystemSettings(
        tenant_id=tenant.id,
        parking_name=request.parking_name,
        notifications_enabled=True,
    ))
    for rule in DEFAULT_BILLING_RULES:
        db.add(BillingRule(tenant_id=tenant.id, **rule))

    request.status = SubscriptionRequestStatus.approved
    request.admin_notes = payload.admin_notes
    request.reviewed_at = now
    request.reviewed_by_id = current_user.id
    request.tenant_id = tenant.id

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not approve request because tenant or owner credentials conflict.",
        ) from exc

    await db.refresh(request)
    await db.refresh(tenant)
    return SubscriptionApprovalOut(
        request=request,
        tenant=tenant,
        owner_mobile=owner.mobile,
        temporary_password=temporary_password,
    )


@router.post("/platform/subscription-requests/{request_id}/reject", response_model=SubscriptionRequestOut)
async def reject_subscription_request(
    request_id: uuid.UUID,
    payload: SubscriptionRequestDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    result = await db.execute(select(SubscriptionRequest).where(SubscriptionRequest.id == request_id))
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription request not found")
    if request.status != SubscriptionRequestStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription request already reviewed")

    request.status = SubscriptionRequestStatus.rejected
    request.admin_notes = payload.admin_notes
    request.reviewed_at = datetime.now(timezone.utc)
    request.reviewed_by_id = current_user.id
    await db.flush()
    await db.refresh(request)
    return request
