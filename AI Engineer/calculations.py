"""Shared business rules — mirror in static/js/report.js for live preview."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

# Demo hardcode per PRD prompt
INSURANCE_DEDUCTIBLES_DEMO = Decimal("5000")


def _d(x: Any) -> Decimal:
    if x is None or x == "":
        return Decimal("0")
    return Decimal(str(x))


def retirement_total(blob: str | dict) -> Decimal:
    if isinstance(blob, str):
        data = json.loads(blob or "{}")
    else:
        data = blob or {}
    return sum((_d(v) for v in data.values()), Decimal("0"))


def non_retirement_total(blob: str | list) -> Decimal:
    if isinstance(blob, str):
        rows = json.loads(blob or "[]")
    else:
        rows = blob or []
    return sum((_d(r.get("balance")) for r in rows), Decimal("0"))


def liabilities_list(blob: str | list) -> list[dict[str, Any]]:
    if isinstance(blob, str):
        return json.loads(blob or "[]")
    return list(blob or [])


def liabilities_sum(blob: str | list) -> Decimal:
    rows = liabilities_list(blob)
    return sum((_d(r.get("balance")) for r in rows), Decimal("0"))


def compute_all(
    *,
    inflow: Any,
    outflow: Any,
    monthly_expense_budget: Any,
    retirement_c1_json: str,
    retirement_c2_json: str,
    non_retirement_json: str,
    trust_zillow_value: Any,
    liabilities_json: str,
) -> dict[str, Decimal]:
    """SACS + TCC figures. Liabilities are reported separately — not netted from net worth."""

    inf = _d(inflow)
    out = _d(outflow)
    excess = inf - out
    monthly_exp = _d(monthly_expense_budget)
    private_reserve_target = monthly_exp * 6 + INSURANCE_DEDUCTIBLES_DEMO

    c1_ret = retirement_total(retirement_c1_json)
    c2_ret = retirement_total(retirement_c2_json)
    non_ret = non_retirement_total(non_retirement_json)
    trust = _d(trust_zillow_value)
    grand_total_net_worth = c1_ret + c2_ret + non_ret + trust
    liab_sum = liabilities_sum(liabilities_json)

    return {
        "excess": excess,
        "private_reserve_target": private_reserve_target,
        "client1_retirement_total": c1_ret,
        "client2_retirement_total": c2_ret,
        "non_retirement_total": non_ret,
        "trust_value": trust,
        "grand_total_net_worth": grand_total_net_worth,
        "liabilities_total": liab_sum,
    }


def metrics_for_client_report(client, report) -> dict:
    """Decimal-safe dict for templates (floats for Jinja/display)."""

    m = compute_all(
        inflow=report.inflow,
        outflow=report.outflow,
        monthly_expense_budget=client.agreed_monthly_expense_budget,
        retirement_c1_json=report.retirement_c1_json,
        retirement_c2_json=report.retirement_c2_json,
        non_retirement_json=report.non_retirement_json,
        trust_zillow_value=report.trust_zillow_value,
        liabilities_json=report.liabilities_json,
    )
    return {k: float(v) for k, v in m.items()}
