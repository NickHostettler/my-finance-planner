"""
Example Usage Script

Demonstrates how to use the Personal Finance Calculator
"""

from personal_finance.calculator import FinanceCalculator
import json


def main():
    """Run example calculations"""
    
    print("=" * 80)
    print("🇨🇭 Swiss Personal Finance Planning Tool - Example Usage")
    print("=" * 80)
    print()
    
    # Initialize calculator with sample data
    calc = FinanceCalculator(
        monthly_net_income=5000,  # CHF
        current_age=35,
        retirement_age=65,
        assumed_annual_return=0.04,
        inflation_rate=0.02,
    )
    
    print("📊 Eingaben:")
    print(f"  • Monatliches Nettoeinkommen: CHF {calc.monthly_net_income:,.2f}")
    print(f"  • Aktuelles Alter: {calc.current_age} Jahre")
    print(f"  • Pensionierungsalter: {calc.retirement_age} Jahre")
    print(f"  • Jahre bis Pensionierung: {calc.years_to_retirement} Jahre")
    print()
    
    # Calculate Pillar 2
    print("2️⃣  2. Säule (Berufvorsorge)")
    print("-" * 80)
    pillar2 = calc.calculate_pillar2()
    print(f"  • Versicherbares Einkommen: CHF {pillar2.insurable_salary:,.2f}")
    print(f"  • Arbeitnehmer-Beitrag: CHF {pillar2.annual_contribution_employee:,.2f}/Jahr")
    print(f"  • Arbeitgeber-Beitrag: CHF {pillar2.annual_contribution_employer:,.2f}/Jahr")
    print(f"  • Gesamtbeitrag: CHF {pillar2.annual_contribution_total:,.2f}/Jahr")
    print(f"  • Monatlich (Total): CHF {pillar2.annual_contribution_total/12:,.2f}")
    print(f"  • Geschätztes Kapital bei Pensionierung: CHF {pillar2.estimated_capital_at_retirement:,.0f}")
    print()
    
    # Calculate Pillar 3a Scenarios
    print("3️⃣  3a Sparlösungen - Verschiedene Szenarien")
    print("-" * 80)
    scenarios = calc.get_pillar3a_scenarios()
    
    for scenario_name, scenario in scenarios.items():
        print(f"\n  {scenario_name}:")
        print(f"    • Monatlicher Sparbetrag: CHF {scenario.monthly_savings:,.2f}")
        print(f"    • Jährlicher Sparbetrag: CHF {scenario.annual_savings:,.2f}")
        if scenario.annual_savings_rate:
            print(f"    • Sparquote: {scenario.annual_savings_rate*100:.1f}%")
        print(f"    • Total Einzahlungen: CHF {scenario.total_contributions:,.0f}")
        print(f"    • Gewinn aus Anlagen: CHF {scenario.investment_gains:,.0f}")
        print(f"    • Vermögen bei Pensionierung: CHF {scenario.total_at_retirement:,.0f}")
    print()
    
    # Complete Analysis with Recommendations
    print("📋 Vollständige Analyse & Empfehlungen")
    print("-" * 80)
    analysis = calc.complete_analysis(pillar3a_savings_rate=0.10)
    
    # Summary
    print(f"\n  2. Säule (geschätzt): CHF {analysis.summary['pillar2_estimated_capital']:,.0f}")
    
    moderate_scenario = analysis.pillar3a_scenarios.get('Sparquote 10%')
    if moderate_scenario:
        print(f"  3a Moderate Sparquote (10%): CHF {moderate_scenario.total_at_retirement:,.0f}")
    
    max_scenario = analysis.pillar3a_scenarios.get('Maximum 3a')
    if max_scenario:
        print(f"  3a Maximum: CHF {max_scenario.total_at_retirement:,.0f}")
    
    # Projections
    print(f"\n  Gesamtprognose (moderat): CHF {analysis.summary['total_retirement_capital_moderate']:,.0f}")
    print(f"  Gesamtprognose (best-case): CHF {analysis.summary['total_retirement_capital_best_case']:,.0f}")
    
    # Recommendations
    print(f"\n  Empfehlungen:")
    for i, rec in enumerate(analysis.summary['recommendations'], 1):
        print(f"    {i}. {rec}")
    
    print()
    print("=" * 80)
    print("✅ Analyse abgeschlossen!")
    print()
    print("💡 Tipp: Starten Sie das Dash Dashboard mit:")
    print("   $ uv run swiss-finance-dashboard")
    print("=" * 80)


if __name__ == '__main__':
    main()
