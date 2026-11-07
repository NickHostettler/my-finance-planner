"""
3b Solutions Module (Freie Vorsorge)

Berechnet private Sparlösungen für die 3. Säule ohne Limite.
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
import math
from personal_finance import config


@dataclass
class Pillar3bScenario:
    """Ergebnis eines 3b privaten Sparszenarios"""
    scenario_name: str
    monthly_savings: float              # CHF pro Monat
    annual_savings: float               # CHF pro Jahr
    annual_savings_rate: Optional[float]  # Sparquote (z.B. 0.20 = 20%)
    years_to_retirement: int
    assumed_annual_return: float        # Angenommene jährliche Rendite
    total_at_retirement: float          # Gesamtvermögen bei Pensionierung
    total_contributions: float          # Summe aller Einzahlungen
    investment_gains: float             # Gewinn aus Kapitalanlagen
    yearly_breakdown: List[Dict]        # Jahr-für-Jahr Breakdown


class Pillar3bCalculator:
    """Berechnet 3b Sparlösungen (Freie Vorsorge ohne Limite)"""
    
    def __init__(self, 
                 annual_net_income: float, 
                 current_age: int, 
                 retirement_age: int = 65,
                 assumed_annual_return: float = 0.04):
        """
        Initialize Pillar 3b Calculator
        
        Args:
            annual_net_income: Jährliches Nettoeinkommen in CHF
            current_age: Aktuelles Alter
            retirement_age: Pensionierungsalter (Standard: 65)
            assumed_annual_return: Angenommene jährliche Rendite (Standard: 4%)
        """
        self.annual_net_income = annual_net_income
        self.current_age = current_age
        self.retirement_age = retirement_age
        self.years_to_retirement = max(0, retirement_age - current_age)
        self.assumed_annual_return = assumed_annual_return
    
    def calculate_by_savings_rate(self, 
                                  savings_rate: float, 
                                  scenario_name: str = "3b Sparquote") -> Pillar3bScenario:
        """
        Berechne 3b Szenario basierend auf einer Sparquote
        
        Args:
            savings_rate: Sparquote (z.B. 0.20 für 20%)
            scenario_name: Name des Szenarios
        
        Returns:
            Pillar3bScenario mit Prognose
        """
        annual_savings = self.annual_net_income * savings_rate
        monthly_savings = annual_savings / 12
        
        return self._calculate_scenario(
            monthly_savings=monthly_savings,
            annual_savings=annual_savings,
            savings_rate=savings_rate,
            scenario_name=f"{scenario_name} ({savings_rate*100:.0f}%)",
        )
    
    def calculate_by_monthly_amount(self, 
                                   monthly_amount: float,
                                   scenario_name: str = "3b Fixbetrag") -> Pillar3bScenario:
        """
        Berechne 3b Szenario basierend auf fixem monatlichem Betrag
        
        Args:
            monthly_amount: Monatlicher Sparbetrag in CHF
            scenario_name: Name des Szenarios
        
        Returns:
            Pillar3bScenario mit Prognose
        """
        annual_savings = monthly_amount * 12
        
        # Berechne Sparquote
        savings_rate = annual_savings / self.annual_net_income if self.annual_net_income > 0 else 0
        
        return self._calculate_scenario(
            monthly_savings=monthly_amount,
            annual_savings=annual_savings,
            savings_rate=savings_rate,
            scenario_name=f"{scenario_name} ({monthly_amount:.0f} CHF/Monat)",
        )
    
    def _calculate_scenario(self,
                           monthly_savings: float,
                           annual_savings: float,
                           savings_rate: Optional[float],
                           scenario_name: str) -> Pillar3bScenario:
        """
        Interne Methode zur Berechnung eines Szenarios
        """
        r = self.assumed_annual_return
        n = self.years_to_retirement
        
        # Berechne Endkapital mit Compound Interest
        # Formula: FV = PMT * [((1 + r)^n - 1) / r]
        if r == 0:
            total_at_retirement = annual_savings * n
        else:
            total_at_retirement = annual_savings * (((1 + r) ** n - 1) / r)
        
        total_contributions = annual_savings * n
        investment_gains = total_at_retirement - total_contributions
        
        # Erstelle Jahr-für-Jahr Breakdown
        yearly_breakdown = self._create_yearly_breakdown(
            annual_savings=annual_savings,
            years=n,
            annual_return=r
        )
        
        return Pillar3bScenario(
            scenario_name=scenario_name,
            monthly_savings=monthly_savings,
            annual_savings=annual_savings,
            annual_savings_rate=savings_rate,
            years_to_retirement=n,
            assumed_annual_return=r,
            total_at_retirement=total_at_retirement,
            total_contributions=total_contributions,
            investment_gains=investment_gains,
            yearly_breakdown=yearly_breakdown,
        )
    
    def _create_yearly_breakdown(self, 
                                annual_savings: float, 
                                years: int,
                                annual_return: float) -> List[Dict]:
        """Erstelle Jahr-für-Jahr Breakdown"""
        breakdown = []
        balance = 0
        r = annual_return
        
        for year in range(1, years + 1):
            # Add savings at beginning of year
            balance += annual_savings
            # Apply returns
            interest = balance * r
            balance += interest
            
            breakdown.append({
                'year': year,
                'age': self.current_age + year,
                'annual_contribution': annual_savings,
                'interest_earned': interest,
                'year_end_balance': balance,
            })
        
        return breakdown
    
    def create_multiple_scenarios(self) -> Dict[str, Pillar3bScenario]:
        """
        Erstelle mehrere vordefinierte Sparlösungen
        
        Returns:
            Dictionary mit verschiedenen Szenarien
        """
        scenarios = {}
        
        # Sparquoten: 10%, 15%, 20%, 25%
        for rate in [0.10, 0.15, 0.20, 0.25]:
            try:
                scenario = self.calculate_by_savings_rate(rate, "3b Sparquote")
                scenarios[f"3b Sparquote {rate*100:.0f}%"] = scenario
            except:
                pass
        
        # Fixbeträge: 500, 1000, 1500, 2000
        for amount in [500, 1000, 1500, 2000]:
            try:
                scenario = self.calculate_by_monthly_amount(amount, "3b Fixbetrag")
                scenarios[f"3b Fixbetrag {amount} CHF/Monat"] = scenario
            except:
                pass
        
        return scenarios
