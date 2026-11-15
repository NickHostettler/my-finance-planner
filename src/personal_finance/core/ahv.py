"""Simplified AHV old-age pension estimate based on official scale-44 bounds."""

import math
from typing import Optional


FULL_CONTRIBUTION_YEARS = 44
# Vollrentenskala 44, gültig ab 1.1.2027 (bis 2026: 1'260 / 2'520).
# Quelle: Medienmitteilung des Bundesrats vom 2.10.2026, config.SOURCE_2027_URL.
MINIMUM_FULL_MONTHLY_PENSION = 1280
MAXIMUM_FULL_MONTHLY_PENSION = 2560
# Die Skala reicht vom 12-fachen bis zum 72-fachen der Minimalrente (AHVG Art. 34).
MINIMUM_PENSION_INCOME = 12 * MINIMUM_FULL_MONTHLY_PENSION  # 15'360
MAXIMUM_PENSION_INCOME = 72 * MINIMUM_FULL_MONTHLY_PENSION  # 92'160
OFFICIAL_LEAFLET_URL = "https://www.ahv-iv.ch/p/3.01.d"

# Erziehungsgutschriften (AHVG Art. 29sexies, Merkblatt 1.07): für jedes Jahr mit einem Kind
# unter 16 die dreifache minimale jährliche Altersrente, eine Gutschrift pro Jahr, egal wie
# viele Kinder. Nicht für das Geburtsjahr, aber für das Jahr, in dem das Kind 16 wird. Bei
# Ehepaaren wird sie für die Ehejahre hälftig aufgeteilt.
EDUCATION_CREDIT = 3 * 12 * MINIMUM_FULL_MONTHLY_PENSION  # 46'080 pro Jahr ab 2027
EDUCATION_CREDIT_CHILD_AGE = 16
EDUCATION_CREDIT_URL = "https://www.ahv-iv.ch/p/1.07.d"

# Plafonierung (AHVG Art. 35): Die beiden Renten eines Ehepaars betragen zusammen höchstens
# 150 % der maximalen Altersrente. Gilt auch für eingetragene Partnerschaften, nicht für
# unverheiratete Paare. Quelle: Merkblatt 3.01 «Altersrenten und Hilflosenentschädigungen der
# AHV» (OFFICIAL_LEAFLET_URL), Stand 1.1.2027.
COUPLE_CAP_RATE = 1.5
COUPLE_MAXIMUM_MONTHLY_PENSION = COUPLE_CAP_RATE * MAXIMUM_FULL_MONTHLY_PENSION  # 3'840


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

    income_fraction = (average_annual_income - MINIMUM_PENSION_INCOME) / (
        MAXIMUM_PENSION_INCOME - MINIMUM_PENSION_INCOME
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
