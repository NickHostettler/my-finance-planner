"""
Savings Module

Verarbeitet Sparquoten und monatliche Sparberechnungen.
"""

from dataclasses import dataclass


@dataclass
class SavingsAnalysis:
    """Analyse der Sparfähigkeit"""
    monthly_net_income: float
    monthly_expenses_max: float       # Maximale monatliche Ausgaben (100% - Sparen)
    savings_rate: float               # Sparquote (z.B. 0.10 = 10%)
    savings_per_month: float          # Sparbetrag pro Monat
    savings_per_year: float           # Sparbetrag pro Jahr
    remaining_income: float           # Verbleibendes Einkommen nach Sparen


class SavingsCalculator:
    """Berechnet Sparquoten und Sparbeträge"""

    def __init__(self, monthly_net_income: float):
        """
        Initialize Savings Calculator

        Args:
            monthly_net_income: Monatliches Nettoeinkommen in CHF
        """
        self.monthly_net_income = monthly_net_income
        self.annual_net_income = monthly_net_income * 12

    def analyze_by_savings_rate(self, savings_rate: float) -> SavingsAnalysis:
        """
        Analysiere Sparfähigkeit basierend auf Sparquote

        Args:
            savings_rate: Sparquote (z.B. 0.10 für 10%)

        Returns:
            SavingsAnalysis mit Detailangaben
        """
        if savings_rate < 0 or savings_rate > 1:
            raise ValueError("Sparquote muss zwischen 0 und 1 liegen")

        monthly_savings = self.monthly_net_income * savings_rate
        annual_savings = monthly_savings * 12
        remaining_income = self.monthly_net_income - monthly_savings

        return SavingsAnalysis(
            monthly_net_income=self.monthly_net_income,
            monthly_expenses_max=remaining_income,
            savings_rate=savings_rate,
            savings_per_month=monthly_savings,
            savings_per_year=annual_savings,
            remaining_income=remaining_income,
        )

    def analyze_by_monthly_amount(self, monthly_amount: float) -> SavingsAnalysis:
        """
        Analysiere Sparfähigkeit basierend auf festem monatlichem Betrag

        Args:
            monthly_amount: Monatlicher Sparbetrag in CHF

        Returns:
            SavingsAnalysis mit Detailangaben
        """
        if monthly_amount < 0:
            raise ValueError("Monatlicher Sparbetrag kann nicht negativ sein")

        if monthly_amount > self.monthly_net_income:
            raise ValueError(
                f"Monatlicher Sparbetrag ({monthly_amount} CHF) darf nicht höher als "
                f"Nettoeinkommen ({self.monthly_net_income} CHF) sein"
            )

        annual_savings = monthly_amount * 12
        savings_rate = monthly_amount / self.monthly_net_income
        remaining_income = self.monthly_net_income - monthly_amount

        return SavingsAnalysis(
            monthly_net_income=self.monthly_net_income,
            monthly_expenses_max=remaining_income,
            savings_rate=savings_rate,
            savings_per_month=monthly_amount,
            savings_per_year=annual_savings,
            remaining_income=remaining_income,
        )
