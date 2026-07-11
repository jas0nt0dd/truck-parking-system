"""
Billing engine.

Rules are loaded fresh from the database (admin-configurable, no code
changes needed). Two kinds of rules are supported:

  * Bracket rules: `from_hours < duration_hours <= to_hours` -> flat `charge`
  * Open-ended rules (`to_hours IS NULL`): apply once `duration_hours >
    from_hours`, charging `charge` per additional day (ceil-rounded),
    e.g. "Additional Day = ₹100" beyond the first 24 hours.

The default seeded rules implement the example in the spec:
  - First 12 Hours = ₹100   (0 < h <= 12)
  - 12-24 Hours    = ₹150   (12 < h <= 24)
  - Additional Day = ₹100   (h > 24, per day, ceil-rounded)
"""
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from app.models.billing_rule import BillingRule


class BillingError(Exception):
    pass


def calculate_charge(
    duration_hours: float, rules: Sequence[BillingRule]
) -> tuple[Decimal, list[dict]]:
    """
    Returns (total_charge, breakdown) where breakdown is a list of
    {"rule_name": str, "amount": Decimal} entries, suitable for storing
    as JSON on the Payment row and for display in the exit summary.
    """
    if duration_hours < 0:
        raise BillingError("duration_hours cannot be negative")

    active_rules = [r for r in rules if r.is_active]
    if not active_rules:
        raise BillingError("No active billing rules configured")

    total = Decimal("0.00")
    breakdown: list[dict] = []

    for rule in sorted(active_rules, key=lambda r: r.priority):
        from_hours = Decimal(str(rule.from_hours))
        charge = Decimal(str(rule.charge))

        if rule.to_hours is not None:
            to_hours = Decimal(str(rule.to_hours))
            if from_hours < Decimal(str(duration_hours)) <= to_hours:
                total += charge
                breakdown.append({"rule_name": rule.rule_name, "amount": str(charge)})
        else:
            # Open-ended rule, e.g. "Additional Day" beyond from_hours.
            if Decimal(str(duration_hours)) > from_hours:
                extra_hours = Decimal(str(duration_hours)) - from_hours
                days = math.ceil(float(extra_hours) / 24)
                extra = (charge * days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total += extra
                breakdown.append(
                    {"rule_name": rule.rule_name, "amount": str(extra), "days": days}
                )

    if total == Decimal("0.00") and not breakdown:
        raise BillingError(
            "No billing rule matched this duration -- check rule coverage in admin panel"
        )

    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), breakdown
