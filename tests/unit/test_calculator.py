"""
Test Suite for Personal Finance Calculator
"""

import pytest
from personal_finance.calculator import FinanceCalculator
from personal_finance.core.pillar_2 import Pillar2Calculator
from personal_finance.core.pillar_3a import Pillar3aCalculator
from personal_finance.core.savings import SavingsCalculator


class TestPillar2:
    """Tests für 2. Säule Berechnung"""
    
    def test_minimum_salary_no_insurance(self):
        """Einkommen unter Minimum hat keine Versicherung"""
        calc = Pillar2Calculator(annual_net_income=20000, current_age=35)
        result = calc.calculate()
        
        assert result.annual_contribution_total == 0
        assert result.estimated_capital_at_retirement == 0
    
    def test_basic_contribution_calculation(self):
        """Berechne Beitrag für normales Einkommen"""
        calc = Pillar2Calculator(annual_net_income=60000, current_age=35)
        result = calc.calculate()
        
        assert result.annual_contribution_total > 0
        assert result.annual_contribution_employee > 0
        assert result.annual_contribution_employer > 0
        # Check 50/50 split
        assert abs(
            result.annual_contribution_employee - result.annual_contribution_employer
        ) < 1  # Allow rounding
    
    def test_age_based_contribution_rates(self):
        """Verschiedene Alter sollten unterschiedliche Beitragssätze haben"""
        young_calc = Pillar2Calculator(annual_net_income=60000, current_age=25)
        middle_calc = Pillar2Calculator(annual_net_income=60000, current_age=45)
        old_calc = Pillar2Calculator(annual_net_income=60000, current_age=55)
        
        young_result = young_calc.calculate()
        middle_result = middle_calc.calculate()
        old_result = old_calc.calculate()
        
        # Older age = higher contribution rate
        assert young_result.annual_contribution_total < middle_result.annual_contribution_total
        assert middle_result.annual_contribution_total < old_result.annual_contribution_total


class TestPillar3a:
    """Tests für 3a Berechnung"""
    
    def test_savings_rate_calculation(self):
        """Berechne 3a mit Sparquote"""
        calc = Pillar3aCalculator(annual_net_income=60000, current_age=35)
        result = calc.calculate_by_savings_rate(0.10)
        
        expected_annual = 60000 * 0.10
        assert result.annual_savings == expected_annual
        assert result.total_at_retirement > result.total_contributions
    
    def test_fixed_amount_calculation(self):
        """Berechne 3a mit festem Betrag"""
        calc = Pillar3aCalculator(annual_net_income=60000, current_age=35)
        result = calc.calculate_by_monthly_amount(500)
        
        assert result.monthly_savings == 500
        assert result.annual_savings == 6000
    
    def test_maximum_annual_limit(self):
        """3a Grenzwert sollte nicht überschritten werden"""
        calc = Pillar3aCalculator(annual_net_income=200000, current_age=35)  # Very high income
        result = calc.calculate_by_savings_rate(0.20)
        
        assert result.annual_savings == 7258

    def test_fixed_monthly_amount_is_capped_at_7258_per_year(self):
        calc = Pillar3aCalculator(annual_net_income=200000, current_age=35)
        result = calc.calculate_by_monthly_amount(1000)

        assert result.annual_savings == 7258
        assert result.monthly_savings == pytest.approx(7258 / 12)
    
    def test_investment_gains(self):
        """Investitionsgewinne sollten > 0 sein"""
        calc = Pillar3aCalculator(annual_net_income=60000, current_age=35)
        result = calc.calculate_by_savings_rate(0.10)
        
        assert result.investment_gains > 0
        assert result.investment_gains == (
            result.total_at_retirement - result.total_contributions
        )


class TestSavingsCalculator:
    """Tests für Sparrechner"""
    
    def test_savings_rate_analysis(self):
        """Analysiere Sparquote"""
        calc = SavingsCalculator(monthly_net_income=5000)
        analysis = calc.analyze_by_savings_rate(0.10)
        
        assert analysis.savings_per_month == 500
        assert analysis.savings_per_year == 6000
        assert analysis.remaining_income == 4500
    
    def test_monthly_amount_analysis(self):
        """Analysiere monatlichen Sparbetrag"""
        calc = SavingsCalculator(monthly_net_income=5000)
        analysis = calc.analyze_by_monthly_amount(800)
        
        assert analysis.savings_per_month == 800
        assert analysis.remaining_income == 4200
    
    def test_validation_exceeds_income(self):
        """Validierung: Sparbetrag darf nicht höher als Einkommen sein"""
        calc = SavingsCalculator(monthly_net_income=5000)
        
        with pytest.raises(ValueError):
            calc.analyze_by_monthly_amount(6000)


class TestFinanceCalculator:
    """Tests für Haupt-Calculator"""
    
    def test_complete_analysis(self):
        """Führe vollständige Analyse durch"""
        calc = FinanceCalculator(
            monthly_net_income=5000,
            current_age=35,
            retirement_age=65,
        )
        
        analysis = calc.complete_analysis()
        
        assert analysis.pillar2 is not None
        assert len(analysis.pillar3a_scenarios) > 0
        assert analysis.savings_analysis is not None
        assert analysis.summary is not None
    
    def test_calculator_initialization(self):
        """Teste Calculator-Initialisierung"""
        calc = FinanceCalculator(
            monthly_net_income=5000,
            current_age=35,
            retirement_age=65,
        )
        
        assert calc.monthly_net_income == 5000
        assert calc.annual_net_income == 60000
        assert calc.years_to_retirement == 30
    
    def test_recommendations_generated(self):
        """Empfehlungen sollten generiert werden"""
        calc = FinanceCalculator(
            monthly_net_income=5000,
            current_age=35,
        )
        
        analysis = calc.complete_analysis()
        assert len(analysis.summary['recommendations']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
