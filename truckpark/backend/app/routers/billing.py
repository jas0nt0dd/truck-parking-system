import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, require_same_tenant, tenant_filter
from app.db.session import get_db
from app.models.billing_rule import BillingRule
from app.models.user import User
from app.schemas.billing import BillingRuleCreate, BillingRuleOut, BillingRuleUpdate

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/rules", response_model=list[BillingRuleOut])
async def list_rules(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)):
    query = select(BillingRule).order_by(BillingRule.priority.asc())
    scope = tenant_filter(BillingRule, current_user)
    if scope is not None:
        query = query.where(scope)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/rules", response_model=BillingRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: BillingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rule = BillingRule(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=BillingRuleOut)
async def update_rule(
    rule_id: uuid.UUID,
    payload: BillingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(BillingRule).where(BillingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing rule not found")
    require_same_tenant(rule, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    if rule.to_hours is not None and rule.to_hours <= rule.from_hours:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="to_hours must be greater than from_hours")

    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(BillingRule).where(BillingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing rule not found")
    require_same_tenant(rule, current_user)
    await db.delete(rule)
