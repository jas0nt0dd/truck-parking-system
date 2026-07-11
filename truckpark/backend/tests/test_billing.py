"""
Unit tests for the billing engine -- the most business-critical piece
of logic in the system. Run with: pytest tests/test_billing.py
"""
from decimal import Decimal

import pytest

from app.services.billing import BillingError, calculate_charge


class FakeRule:
    def __init__(self, rule_name, from_hours, to_hours, charge, priority=1, is_active=True):
        self.rule_name = rule_name
        self.from_hours = from_hours
        self.to_hours = to_hours
        self.charge = charge
        self.priority = priority
        self.is_active = is_active


DEFAULT_RULES = [
    FakeRule("First 12 Hours", 0, 12, 100, priority=1),
    FakeRule("12-24 Hours", 12, 24, 150, priority=2),
    FakeRule("Additional Day", 24, None, 100, priority=3),
]


def test_within_first_bracket():
    total, breakdown = calculate_charge(5, DEFAULT_RULES)
    assert total == Decimal("100.00")
    assert breakdown[0]["rule_name"] == "First 12 Hours"


def test_exactly_12_hours():
    total, _ = calculate_charge(12, DEFAULT_RULES)
    assert total == Decimal("100.00")


def test_second_bracket():
    total, _ = calculate_charge(18, DEFAULT_RULES)
    assert total == Decimal("150.00")


def test_open_ended_one_extra_day():
    total, breakdown = calculate_charge(30, DEFAULT_RULES)  # 6 hrs past 24h -> 1 day
    assert total == Decimal("100.00")
    assert breakdown[0]["days"] == 1


def test_open_ended_two_extra_days():
    total, breakdown = calculate_charge(50, DEFAULT_RULES)  # 26 hrs past 24h -> ceil(26/24)=2 days
    assert total == Decimal("200.00")
    assert breakdown[0]["days"] == 2


def test_no_active_rules_raises():
    with pytest.raises(BillingError):
        calculate_charge(5, [])


def test_negative_duration_raises():
    with pytest.raises(BillingError):
        calculate_charge(-1, DEFAULT_RULES)


def test_inactive_rule_ignored():
    rules = [FakeRule("Inactive", 0, 100, 999, is_active=False)]
    with pytest.raises(BillingError):
        calculate_charge(5, rules)
