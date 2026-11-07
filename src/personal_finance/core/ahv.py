"""Simplified AHV old-age pension estimate based on official scale-44 bounds."""

import math
from typing import Optional


FULL_CONTRIBUTION_YEARS = 44
MINIMUM_FULL_MONTHLY_PENSION = 1260
MAXIMUM_FULL_MONTHLY_PENSION = 2520
MINIMUM_PENSION_INCOME = 15120
MAXIMUM_PENSION_INCOME = 90720
OFFICIAL_LEAFLET_URL = "https://www.ahv-iv.ch/p/3.01.d"


def estimate_monthly_old_age_pension(
    average_annual_income: float,
    contribution_years: int,
) -> float:
    """Estimate a monthly pension by interpolating scale-44 official bounds.

    The interpolation is only a comparison estimate. It does not reproduce the
    official pension table or account for credits, income splitting, rounding,
    transition-generation supplements, or individual contribution records.
    """
    if not math.isfinite(average_annual_income) or average_annual_income < 0:
        raise ValueError("Das durchschnittliche Jahreseinkommen darf nicht negativ sein.")
    if (
        not isinstance(contribution_years, int)
        or not 0 <= contribution_years <= FULL_CONTRIBUTION_YEARS
    ):
        raise ValueError(
            f"Die Beitragsjahre müssen zwischen 0 und {FULL_CONTRIBUTION_YEARS} liegen."
        )

    income_fraction = (
        (average_annual_income - MINIMUM_PENSION_INCOME)
        / (MAXIMUM_PENSION_INCOME - MINIMUM_PENSION_INCOME)
    )
    income_fraction = min(1.0, max(0.0, income_fraction))
    full_monthly_pension = MINIMUM_FULL_MONTHLY_PENSION + income_fraction * (
        MAXIMUM_FULL_MONTHLY_PENSION - MINIMUM_FULL_MONTHLY_PENSION
    )
    return full_monthly_pension * contribution_years / FULL_CONTRIBUTION_YEARS


def project_pension_basis(
    monthly_pension_today: Optional[float],
    years_until_retirement: int,
    annual_inflation: float,
    display_basis: str,
) -> Optional[float]:
    """Express a current-law pension estimate in the selected CHF basis."""
    if monthly_pension_today is None:
        return None
    if (
        not math.isfinite(monthly_pension_today)
        or monthly_pension_today < 0
        or years_until_retirement < 0
        or annual_inflation <= -1
        or display_basis not in {"nominal", "real"}
    ):
        raise ValueError("Ungültige Eingaben für die AHV-Rentenprojektion.")
    if display_basis == "real":
        return monthly_pension_today
    return monthly_pension_today * ((1 + annual_inflation) ** years_until_retirement)
