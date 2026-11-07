"""
Swiss Salary Deductions Calculator

Schätzt die Lohnabzüge nach Schweizer Recht (AHV/IV/EO, ALV, NBU) sowie Krankenkasse,
Pensionskasse und eine grobe Einkommenssteuer. Sätze und Höchstlöhne stehen in ``config``.
"""

from dataclasses import dataclass
from typing import Dict

from personal_finance import config


@dataclass
class SalaryDeductions:
    """Ergebnis der Lohnabzug-Berechnung (alle Beträge in CHF pro Monat)."""

    gross_monthly_income: float

    # Sozialversicherungen (Arbeitnehmer)
    ahv_iv_eo: float           # AHV/IV/EO auf dem ganzen Lohn
    alv: float                 # ALV bis zum Höchstlohn
    nbu: float                 # Nichtberufsunfall bis zum UVG-Höchstlohn

    # Weitere Abzüge
    krankenkasse: float        # Durchschnittliche Krankenkassenprämie (Annahme)
    pensionskasse: float       # 2. Säule Beitrag Arbeitnehmer

    # Steuerschätzung (grob)
    income_tax: float

    # Summen
    total_employee_deductions: float
    net_monthly_income: float

    # Arbeitgeber-Anteile (informativ)
    employer_ahv_iv_eo: float
    employer_alv: float
    employer_pensionskasse: float


def _capped_monthly_base(gross_monthly_income: float, max_annual_salary: float) -> float:
    """Monatlicher Lohn, auf den ein Beitrag mit jährlichem Höchstlohn erhoben wird."""
    return min(gross_monthly_income, max_annual_salary / 12)


class DeductionsCalculator:
    """Berechnet Schweizer Lohnabzüge"""

    def __init__(
        self,
        gross_monthly_income: float,
        employee_pillar2_contribution: float = 0,
        canton: str = "ZH",
        avg_health_insurance: float = config.AVERAGE_HEALTH_INSURANCE_MONTHLY,
    ):
        """
        Args:
            gross_monthly_income: Bruttolohn pro Monat in CHF
            employee_pillar2_contribution: Arbeitnehmer-Beitrag 2. Säule in CHF/Monat
            canton: Kanton für Steuerschätzung (Standard: ZH)
            avg_health_insurance: Durchschn. Krankenkassenprämie/Monat
        """
        self.gross_monthly_income = gross_monthly_income
        self.gross_annual_income = gross_monthly_income * 12
        self.employee_pillar2_contribution = employee_pillar2_contribution
        self.canton = canton
        self.avg_health_insurance = avg_health_insurance

    def calculate(self) -> SalaryDeductions:
        """Berechne alle Lohnabzüge."""
        gross = self.gross_monthly_income
        alv_base = _capped_monthly_base(gross, config.ALV_MAX_INSURED_ANNUAL_SALARY)
        uvg_base = _capped_monthly_base(gross, config.UVG_MAX_INSURED_ANNUAL_SALARY)

        ahv_iv_eo = gross * config.AHV_IV_EO_RATE
        alv = alv_base * config.ALV_RATE
        nbu = uvg_base * config.NBU_RATE
        krankenkasse = self.avg_health_insurance
        pensionskasse = self.employee_pillar2_contribution
        income_tax = self._estimate_income_tax()

        total_deductions = ahv_iv_eo + alv + nbu + krankenkasse + pensionskasse + income_tax

        return SalaryDeductions(
            gross_monthly_income=gross,
            ahv_iv_eo=ahv_iv_eo,
            alv=alv,
            nbu=nbu,
            krankenkasse=krankenkasse,
            pensionskasse=pensionskasse,
            income_tax=income_tax,
            total_employee_deductions=total_deductions,
            net_monthly_income=gross - total_deductions,
            employer_ahv_iv_eo=gross * config.AHV_IV_EO_RATE_EMPLOYER,
            employer_alv=alv_base * config.ALV_RATE_EMPLOYER,
            employer_pensionskasse=self.employee_pillar2_contribution,
        )

    def _estimate_income_tax(self) -> float:
        """Grobe Schätzung der monatlichen Einkommenssteuer in CHF."""
        rate = config.get_canton_tax_rate(self.canton)
        annual_taxable_income = max(0, self.gross_annual_income - config.ANNUAL_TAX_ALLOWANCE)
        return annual_taxable_income * rate / 12

    def get_summary(self) -> Dict:
        """Erstelle Summary der Lohnabzüge"""
        result = self.calculate()

        return {
            'gross_monthly': result.gross_monthly_income,
            'gross_annual': self.gross_annual_income,
            'net_monthly': result.net_monthly_income,
            'net_annual': result.net_monthly_income * 12,
            'deductions': {
                'ahv_iv_eo': result.ahv_iv_eo,
                'alv': result.alv,
                'nbu': result.nbu,
                'krankenkasse': result.krankenkasse,
                'pensionskasse': result.pensionskasse,
                'income_tax': result.income_tax,
            },
            'total_deductions': result.total_employee_deductions,
            'net_rate': (
                result.net_monthly_income / result.gross_monthly_income
                if result.gross_monthly_income
                else 0.0
            ),
        }
