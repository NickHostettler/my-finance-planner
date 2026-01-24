"""
Savings Module

Verarbeitet Sparquoten und monatliche Sparberechnungen.
"""

from dataclasses import dataclass
from typing import Dict, Optional


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
    
    def get_recommended_savings_rates(self) -> Dict[str, Dict]:
        """
        Ermittle empfohlene Sparquoten basierend auf Best Practices
        
        Returns:
            Dictionary mit verschiedenen Szenarios
        """
        return {
            'conservative': {
                'rate': 0.05,
                'description': 'Konservativ (5%)',
                'monthly': self.monthly_net_income * 0.05,
            },
            'moderate': {
                'rate': 0.10,
                'description': 'Moderat (10%)',
                'monthly': self.monthly_net_income * 0.10,
            },
            'aggressive': {
                'rate': 0.15,
                'description': 'Aggressiv (15%)',
                'monthly': self.monthly_net_income * 0.15,
            },
            'very_aggressive': {
                'rate': 0.20,
                'description': 'Sehr Aggressiv (20%)',
                'monthly': self.monthly_net_income * 0.20,
            },
        }
    
    def validate_total_savings(self,
                             pillar2_monthly: float,
                             pillar3a_monthly: float,
                             other_monthly: Optional[float] = 0) -> Dict:
        """
        Validiere, ob Gesamtsparen realistisch ist
        
        Args:
            pillar2_monthly: Monatlicher 2. Säule Beitrag (meist vom Arbeitgeber gezahlt)
            pillar3a_monthly: Monatlicher 3a Sparbetrag
            other_monthly: Andere Sparbeiträge
        
        Returns:
            Dictionary mit Validierungsergebnissen
        """
        other_monthly = other_monthly or 0
        total_savings = pillar3a_monthly + other_monthly
        
        if total_savings > self.monthly_net_income:
            return {
                'valid': False,
                'message': f'Gesamtsparen ({total_savings:.2f} CHF) überschreitet Nettoeinkommen ({self.monthly_net_income:.2f} CHF)',
                'total_savings': total_savings,
                'remaining_income': self.monthly_net_income - total_savings,
            }
        
        remaining = self.monthly_net_income - total_savings
        savings_rate = total_savings / self.monthly_net_income
        
        return {
            'valid': True,
            'message': f'Gesamtsparen von {total_savings:.2f} CHF ist realistisch',
            'total_savings': total_savings,
            'savings_rate': savings_rate,
            'remaining_income': remaining,
            'recommendation': self._get_recommendation(savings_rate),
        }
    
    def _get_recommendation(self, savings_rate: float) -> str:
        """Gebe Empfehlung basierend auf Sparquote"""
        if savings_rate < 0.05:
            return "Sehr niedrig - mehr Sparen wäre empfohlen"
        elif savings_rate < 0.10:
            return "Moderat - konservatives Sparziel"
        elif savings_rate < 0.15:
            return "Gut - ausgewogenes Sparziel"
        elif savings_rate < 0.20:
            return "Hoch - aggressives Sparziel"
        else:
            return "Sehr hoch - überprüfe die Realistizität"
