"""
2. Säule (Berufvorsorge) Calculator Module

Berechnet Beiträge und Ansprüche gemäß BVG (Bundesgesetz über die berufliche Altersversorgung)
"""

from dataclasses import dataclass
from typing import Dict, List
import math


@dataclass
class Pillar2Result:
    """Ergebnis der 2. Säule Berechnung"""
    annual_contribution_employee: float  # Arbeitnehmer-Beitrag
    annual_contribution_employer: float  # Arbeitgeber-Beitrag
    annual_contribution_total: float     # Gesamtbeitrag
    coordination_deduction: float        # Koordinationsabzug
    insurable_salary: float              # Versicherbares Einkommen
    years_until_retirement: int
    estimated_capital_at_retirement: float  # Schätzung des Kapitals bei Pensionierung


class Pillar2Calculator:
    """Berechnet 2. Säule (Berufvorsorge) nach BVG"""
    
    # 2024 Werte - können jährlich angepasst werden
    MIN_SALARY = 24885  # CHF Mindestlohn für Versicherung
    COORDINATION_DEDUCTION = 24885  # CHF Koordinationsabzug
    MAX_PILLAR2_RATE = 0.15  # Max. 15% Beitragssatz
    ASSUMED_ANNUAL_RETURN = 0.04  # 4% angenommene jährliche Rendite
    
    def __init__(self, annual_net_income: float, current_age: int, retirement_age: int = 65):
        """
        Initialize Pillar 2 Calculator
        
        Args:
            annual_net_income: Jährliches Nettoeinkommen in CHF
            current_age: Aktuelles Alter
            retirement_age: Pensionierungsalter (Standard: 65)
        """
        self.annual_net_income = annual_net_income
        self.current_age = current_age
        self.retirement_age = retirement_age
        self.years_until_retirement = max(0, retirement_age - current_age)
    
    def calculate(self) -> Pillar2Result:
        """
        Berechne 2. Säule Anspruch
        
        Returns:
            Pillar2Result mit detaillierten Angaben
        """
        # Versicherbares Einkommen nach Koordinationsabzug
        insurable_salary = max(0, self.annual_net_income - self.COORDINATION_DEDUCTION)
        
        # Mindestversicherung prüfen
        if self.annual_net_income < self.MIN_SALARY:
            # Unter Minimum - keine Versicherung
            return Pillar2Result(
                annual_contribution_employee=0,
                annual_contribution_employer=0,
                annual_contribution_total=0,
                coordination_deduction=0,
                insurable_salary=0,
                years_until_retirement=self.years_until_retirement,
                estimated_capital_at_retirement=0,
            )
        
        # Beitragssätze nach Alter (typisches Schweizer Schema)
        contribution_rate = self._get_contribution_rate()
        
        # Paritätisches Splitting (50/50)
        total_contribution = insurable_salary * contribution_rate
        employee_contribution = total_contribution * 0.5
        employer_contribution = total_contribution * 0.5
        
        # Schätzung des Kapitals bei Pensionierung mit Compound Interest
        capital_at_retirement = self._estimate_capital_at_retirement(total_contribution)
        
        return Pillar2Result(
            annual_contribution_employee=employee_contribution,
            annual_contribution_employer=employer_contribution,
            annual_contribution_total=total_contribution,
            coordination_deduction=self.COORDINATION_DEDUCTION,
            insurable_salary=insurable_salary,
            years_until_retirement=self.years_until_retirement,
            estimated_capital_at_retirement=capital_at_retirement,
        )
    
    def _get_contribution_rate(self) -> float:
        """
        Ermittle Beitragssatz nach Alter
        
        Typische Schweizer Skala (Arbeitgeber + Arbeitnehmer kombiniert):
        - Bis 24: 7%
        - 25-34: 10%
        - 35-44: 12%
        - 45-54: 14%
        - 55+: 15%
        
        Returns:
            Beitragssatz als Dezimal (z.B. 0.10 = 10%)
        """
        if self.current_age < 25:
            return 0.07
        elif self.current_age < 35:
            return 0.10
        elif self.current_age < 45:
            return 0.12
        elif self.current_age < 55:
            return 0.14
        else:
            return 0.15
    
    def _estimate_capital_at_retirement(self, annual_contribution: float) -> float:
        """
        Schätze das Alterskapital bei Pensionierung
        
        Verwendet Compound Interest Formula mit konstanten jährlichen Beiträgen.
        """
        if self.years_until_retirement <= 0:
            return 0
        
        # Formula: FV = PMT * [((1 + r)^n - 1) / r]
        # Annuity Future Value
        r = self.ASSUMED_ANNUAL_RETURN
        n = self.years_until_retirement
        
        if r == 0:
            return annual_contribution * n
        
        future_value = annual_contribution * (((1 + r) ** n - 1) / r)
        return future_value
    
    def get_monthly_employee_contribution(self) -> float:
        """Ermittle monatlichen Arbeitnehmer-Beitrag"""
        result = self.calculate()
        return result.annual_contribution_employee / 12
    
    def get_monthly_total_contribution(self) -> float:
        """Ermittle monatlichen Gesamtbeitrag (inkl. Arbeitgeber)"""
        result = self.calculate()
        return result.annual_contribution_total / 12
