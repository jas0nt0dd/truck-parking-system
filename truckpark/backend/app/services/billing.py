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
from types import SimpleNamespace
from typing import Sequence

from app.models.billing_rule import BillingRule

DEFAULT_BILLING_RULES = [
    {"rule_name": "First 12 Hours", "from_hours": 0.0, "to_hours": 12.0, "charge": 100.0, "priority": 1},
    {"rule_name": "12-24 Hours", "from_hours": 12.0, "to_hours": 24.0, "charge": 150.0, "priority": 2},
    {"rule_name": "Additional Day", "from_hours": 24.0, "to_hours": None, "charge": 100.0, "priority": 3},
]


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
        active_rules = [SimpleNamespace(**rule) for rule in DEFAULT_BILLING_RULES]

    def _calculate(rules_to_apply):
        total = Decimal("0.00")
        breakdown: list[dict] = []
        duration_amount = Decimal(str(duration_hours))

        finite_rules = [r for r in rules_to_apply if r.to_hours is not None]
        open_rule = next((r for r in rules_to_apply if r.to_hours is None), None)

        selected_rule = None
        for rule in sorted(finite_rules, key=lambda r: r.priority):
            from_hours = Decimal(str(rule.from_hours))
            to_hours = Decimal(str(rule.to_hours))

            if from_hours == Decimal("0.00") and duration_amount == Decimal("0.00"):
                selected_rule = rule
                break
            if from_hours < duration_amount <= to_hours:
                selected_rule = rule
                break

        if selected_rule is not None:
            charge = Decimal(str(selected_rule.charge))
            total += charge
            breakdown.append({"rule_name": selected_rule.rule_name, "amount": str(charge)})
        elif open_rule is not None and duration_amount > Decimal(str(open_rule.from_hours)):
            if finite_rules:
                last_finite = sorted(finite_rules, key=lambda r: r.priority)[-1]
                charge = Decimal(str(last_finite.charge))
                total += charge
                breakdown.append({"rule_name": last_finite.rule_name, "amount": str(charge)})

            extra_hours = duration_amount - Decimal(str(open_rule.from_hours))
            days = math.ceil(float(extra_hours) / 24)
            extra = (Decimal(str(open_rule.charge)) * days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += extra
            breakdown.append({"rule_name": open_rule.rule_name, "amount": str(extra), "days": days})

        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), breakdown

    total, breakdown = _calculate(active_rules)
    if total == Decimal("0.00") and not breakdown:
        if active_rules != [SimpleNamespace(**rule) for rule in DEFAULT_BILLING_RULES]:
            active_rules = [SimpleNamespace(**rule) for rule in DEFAULT_BILLING_RULES]
            total, breakdown = _calculate(active_rules)

    if total == Decimal("0.00") and not breakdown:
        raise BillingError(
            "No billing rule matched this duration -- check rule coverage in admin panel"
        )

    return total, breakdown
