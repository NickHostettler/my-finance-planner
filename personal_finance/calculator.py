"""
Main Finance Calculator Class

Integriert alle Berechnungsmodule für eine umfassende Finanzanalyse.
"""

from typing import Dict, List, Optional
from personal_finance.pillar_2 import Pillar2Calculator, Pillar2Result
from personal_finance.pillar_3a import Pillar3aCalculator, Pillar3aScenario
from personal_finance.pillar_3b import Pillar3bCalculator, Pillar3bScenario
from personal_finance.savings import SavingsCalculator, SavingsAnalysis
from personal_finance.deductions import DeductionsCalculator, SalaryDeductions
from dataclasses import dataclass
from personal_finance import config


@dataclass
class CompleteFinancialAnalysis:
    """Vollständige Finanzanalyse mit allen Szenarien"""
    monthly_net_income: float
    current_age: int
    retirement_age: int
    years_to_retirement: int
    pillar2: Pillar2Result
    pillar3a_scenarios: Dict[str, Pillar3aScenario]
    pillar3b_scenarios: Dict[str, Pillar3bScenario]
    savings_analysis: SavingsAnalysis
    summary: Dict


class FinanceCalculator:
    """
    Hauptklasse für umfassende Schweizer Finanzplanung
    
    Kombiniert:
    - 2. Säule (Berufvorsorge)
    - 3a Sparlösungen
    - Sparquoten & Betrag Verwaltung
    - Gesamtvermögensanalyse
    """
    
    def __init__(self,
                 monthly_net_income: float,
                 current_age: int,
                 retirement_age: int = config.DEFAULT_RETIREMENT_AGE,
                 assumed_annual_return: float = config.ASSUMED_ANNUAL_RETURN,
                 inflation_rate: float = config.INFLATION_RATE):
        """
        Initialize Finance Calculator
        
        Args:
            monthly_net_income: Monatliches Nettoeinkommen in CHF
            current_age: Aktuelles Alter
            retirement_age: Pensionierungsalter (Standard: 65)
            assumed_annual_return: Angenommene jährliche Rendite (Standard: 4%)
            inflation_rate: Jährliche Inflationsrate (Standard: 2%)
        """
        self.monthly_net_income = monthly_net_income
        self.annual_net_income = monthly_net_income * 12
        self.current_age = current_age
        self.retirement_age = retirement_age
        self.assumed_annual_return = assumed_annual_return
        self.inflation_rate = inflation_rate
        self.years_to_retirement = max(0, retirement_age - current_age)
        
        # Initialize sub-calculators
        self.pillar2_calc = Pillar2Calculator(
            annual_net_income=self.annual_net_income,
            current_age=current_age,
            retirement_age=retirement_age
        )
        
        self.pillar3a_calc = Pillar3aCalculator(
            annual_net_income=self.annual_net_income,
            current_age=current_age,
            retirement_age=retirement_age,
            assumed_annual_return=assumed_annual_return
        )
        
        self.pillar3b_calc = Pillar3bCalculator(
            annual_net_income=self.annual_net_income,
            current_age=current_age,
            retirement_age=retirement_age,
            assumed_annual_return=assumed_annual_return
        )
        
        self.savings_calc = SavingsCalculator(
            monthly_net_income=monthly_net_income
        )
    
    def calculate_pillar2(self) -> Pillar2Result:
        """Berechne 2. Säule Anspruch"""
        return self.pillar2_calc.calculate()
    
    def calculate_pillar3a(self,
                         savings_rate: Optional[float] = None,
                         monthly_amount: Optional[float] = None) -> Pillar3aScenario:
        """
        Berechne 3a Szenario
        
        Args:
            savings_rate: Sparquote (z.B. 0.10 für 10%) ODER
            monthly_amount: Monatlicher Sparbetrag in CHF
        
        Returns:
            Pillar3aScenario mit Prognose
        """
        if savings_rate is not None:
            return self.pillar3a_calc.calculate_by_savings_rate(savings_rate)
        elif monthly_amount is not None:
            return self.pillar3a_calc.calculate_by_monthly_amount(monthly_amount)
        else:
            raise ValueError("Entweder savings_rate oder monthly_amount müssen angegeben werden")
    
    def get_pillar3a_scenarios(self) -> Dict[str, Pillar3aScenario]:
        """Erstelle vordefinierte 3a Szenarien"""
        return self.pillar3a_calc.create_multiple_scenarios()
    
    def calculate_pillar3b(self,
                          savings_rate: Optional[float] = None,
                          monthly_amount: Optional[float] = None) -> Pillar3bScenario:
        """
        Berechne 3b Szenario
        
        Args:
            savings_rate: Sparquote (z.B. 0.20 für 20%) ODER
            monthly_amount: Monatlicher Sparbetrag in CHF
        
        Returns:
            Pillar3bScenario mit Prognose
        """
        if savings_rate is not None:
            return self.pillar3b_calc.calculate_by_savings_rate(savings_rate)
        elif monthly_amount is not None:
            return self.pillar3b_calc.calculate_by_monthly_amount(monthly_amount)
        else:
            raise ValueError("Entweder savings_rate oder monthly_amount müssen angegeben werden")
    
    def get_pillar3b_scenarios(self) -> Dict[str, Pillar3bScenario]:
        """Erstelle vordefinierte 3b Szenarien"""
        return self.pillar3b_calc.create_multiple_scenarios()
    
    def calculate_savings_analysis(self,
                                   savings_rate: Optional[float] = None,
                                   monthly_amount: Optional[float] = None) -> SavingsAnalysis:
        """
        Analysiere Sparfähigkeit
        
        Args:
            savings_rate: Sparquote ODER
            monthly_amount: Monatlicher Sparbetrag
        
        Returns:
            SavingsAnalysis mit Details
        """
        if savings_rate is not None:
            return self.savings_calc.analyze_by_savings_rate(savings_rate)
        elif monthly_amount is not None:
            return self.savings_calc.analyze_by_monthly_amount(monthly_amount)
        else:
            raise ValueError("Entweder savings_rate oder monthly_amount müssen angegeben werden")
    
    def complete_analysis(self,
                         pillar3a_savings_rate: float = 0.10,
                         pillar3b_savings_rate: float = 0.10) -> CompleteFinancialAnalysis:
        """
        Erstelle vollständige Finanzanalyse
        
        Args:
            pillar3a_savings_rate: Sparquote für 3a Berechnung (Standard: 10%)
            pillar3b_savings_rate: Sparquote für 3b Berechnung (Standard: 10%)
        
        Returns:
            CompleteFinancialAnalysis mit allen Szenarien
        """
        # Berechne alle Säulen
        pillar2 = self.calculate_pillar2()
        pillar3a_scenarios = self.get_pillar3a_scenarios()
        pillar3b_scenarios = self.get_pillar3b_scenarios()
        savings_analysis = self.calculate_savings_analysis(savings_rate=pillar3a_savings_rate)
        
        # Erstelle Summary
        summary = self._create_summary(pillar2, pillar3a_scenarios, pillar3b_scenarios, savings_analysis)
        
        return CompleteFinancialAnalysis(
            monthly_net_income=self.monthly_net_income,
            current_age=self.current_age,
            retirement_age=self.retirement_age,
            years_to_retirement=self.years_to_retirement,
            pillar2=pillar2,
            pillar3a_scenarios=pillar3a_scenarios,
            pillar3b_scenarios=pillar3b_scenarios,
            savings_analysis=savings_analysis,
            summary=summary,
        )
    
    def _create_summary(self,
                       pillar2: Pillar2Result,
                       pillar3a_scenarios: Dict[str, Pillar3aScenario],
                       pillar3b_scenarios: Dict[str, Pillar3bScenario],
                       savings_analysis: SavingsAnalysis) -> Dict:
        """Erstelle Zusammenfassung der Analyse"""
        
        # Best-Case Szenario (Maximum 3a + Maximum 3b)
        max_3a_scenario = pillar3a_scenarios.get("Maximum 3a")
        moderate_3a_scenario = pillar3a_scenarios.get("Sparquote 10%")
        max_3b_scenario = max(pillar3b_scenarios.values(), key=lambda x: x.total_at_retirement) if pillar3b_scenarios else None
        
        total_best_case = pillar2.estimated_capital_at_retirement
        if max_3a_scenario:
            total_best_case += max_3a_scenario.total_at_retirement
        if max_3b_scenario:
            total_best_case += max_3b_scenario.total_at_retirement
        
        total_moderate = pillar2.estimated_capital_at_retirement
        if moderate_3a_scenario:
            total_moderate += moderate_3a_scenario.total_at_retirement
        
        return {
            'monthly_net_income': self.monthly_net_income,
            'current_age': self.current_age,
            'retirement_age': self.retirement_age,
            'years_to_retirement': self.years_to_retirement,
            
            # 2. Säule
            'pillar2_monthly_contribution': pillar2.annual_contribution_total / 12,
            'pillar2_estimated_capital': pillar2.estimated_capital_at_retirement,
            
            # 3a Overview
            'pillar3a_scenarios_count': len(pillar3a_scenarios),
            
            # 3b Overview
            'pillar3b_scenarios_count': len(pillar3b_scenarios),
            
            # Gesamtszenarien
            'total_retirement_capital_best_case': total_best_case,
            'total_retirement_capital_moderate': total_moderate,
            
            # Empfehlungen
            'recommendations': self._generate_recommendations(pillar2, savings_analysis),
        }
    
    def _generate_recommendations(self,
                                 pillar2: Pillar2Result,
                                 savings_analysis: SavingsAnalysis) -> List[str]:
        """Generiere Empfehlungen basierend auf Analyse"""
        recommendations = []
        
        # 2. Säule Empfehlungen
        if pillar2.annual_contribution_total == 0:
            recommendations.append(
                "⚠️ Ihr Einkommen ist unterhalb der BVG-Mindestversicherung. "
                "Konzentrieren Sie sich auf 3a und private Sparen."
            )
        else:
            monthly_contribution = pillar2.annual_contribution_total / 12
            if monthly_contribution > 1500:
                recommendations.append(
                    f"✅ 2. Säule: Starker Beitrag ({monthly_contribution:.0f} CHF/Monat). "
                    "Nutzen Sie dies maximimal."
                )
        
        # Sparquoten Empfehlungen
        rate = savings_analysis.savings_rate
        if rate < 0.05:
            recommendations.append(
                "💡 Erhöhen Sie Ihre Sparquote auf mindestens 5-10% für bessere Altersvorsorge."
            )
        elif rate > 0.25:
            recommendations.append(
                "⚠️ Ihre Sparquote ist sehr hoch. Überprüfen Sie, ob dies nachhaltig ist."
            )
        
        # 3a Empfehlung
        max_3a = self.pillar3a_calc.get_maximum_annual_pillar3a()
        recommendations.append(
            f"📊 3a: Nutzen Sie die maximale Einzahlung von {max_3a:.0f} CHF/Jahr "
            f"({max_3a/12:.0f} CHF/Monat) für Steuerersparnisse."
        )
        
        # 3b Empfehlung
        recommendations.append(
            f"💰 3b (freie Vorsorge): Zusätzlich zu 3a können Sie unbegrenzt in 3b sparen. "
            f"Mit regelmäßigen Einzahlungen (z.B. 500-2000 CHF/Monat) können Sie ein "
            f"signifikantes Vermögen bis zur Pensionierung aufbauen."
        )
        
        return recommendations
    
    def get_summary_for_dashboard(self) -> Dict:
        """Ermittle Summary für Dashboard-Anzeige"""
        analysis = self.complete_analysis()
        
        return {
            'income': {
                'monthly': self.monthly_net_income,
                'annual': self.annual_net_income,
            },
            'personal_info': {
                'current_age': self.current_age,
                'retirement_age': self.retirement_age,
                'years_to_retirement': self.years_to_retirement,
            },
            'pillar2': {
                'monthly_total': analysis.pillar2.annual_contribution_total / 12,
                'monthly_employee': analysis.pillar2.annual_contribution_employee / 12,
                'monthly_employer': analysis.pillar2.annual_contribution_employer / 12,
                'estimated_capital': analysis.pillar2.estimated_capital_at_retirement,
            },
            'pillar3a': {
                'scenarios': {
                    name: {
                        'monthly': scenario.monthly_savings,
                        'annual': scenario.annual_savings,
                        'total_at_retirement': scenario.total_at_retirement,
                        'contributions': scenario.total_contributions,
                        'gains': scenario.investment_gains,
                    }
                    for name, scenario in analysis.pillar3a_scenarios.items()
                },
            },
            'retirement_projections': analysis.summary,
        }
