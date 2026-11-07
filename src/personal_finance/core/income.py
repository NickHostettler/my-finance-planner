"""Income normalisation (monthly/yearly, gross/net)."""

import math
from typing import Tuple


from personal_finance import config
from personal_finance.core.deductions import DeductionsCalculator
from personal_finance.core.pillar_2 import Pillar2Calculator


def normalize_income(amount, period: str, income_type: str, age: int, canton: str) -> Tuple[float, float]:
    """Return the equivalent monthly net and gross income."""
    if amount is None or not math.isfinite(float(amount)) or amount <= 0:
        raise ValueError("Bitte gib ein Einkommen größer als 0 CHF ein.")
    if period not in {"monthly", "yearly"}:
        raise ValueError("Bitte wähle einen monatlichen oder jährlichen Zeitraum.")
    if income_type not in {"net", "gross"}:
        raise ValueError("Bitte wähle Brutto oder Netto.")

    monthly_amount = float(amount) / 12 if period == "yearly" else float(amount)
    if income_type == "net":
        return monthly_amount, monthly_amount
    if canton not in config.CANTON_TAX_RATES:
        raise ValueError("Bitte wähle einen gültigen Kanton.")

    employee_pillar2 = Pillar2Calculator(
        annual_net_income=monthly_amount * 12,
        current_age=age,
    ).calculate().annual_contribution_employee / 12
    deductions = DeductionsCalculator(
        gross_monthly_income=monthly_amount,
        employee_pillar2_contribution=employee_pillar2,
        canton=canton,
    ).calculate()
    return max(0.0, deductions.net_monthly_income), monthly_amount
