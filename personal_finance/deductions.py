"""
Swiss Salary Deductions Calculator

Berechnet automatische Lohnabzüge nach Schweizer Recht (AHV, IV, NBU, ALV, etc.)
"""

from dataclasses import dataclass
from typing import Dict
from personal_finance import config


@dataclass
class SalaryDeductions:
    """Ergebnis der Lohnabzug-Berechnung"""
    gross_monthly_income: float
    
    # Obligatorische Abzüge (Arbeitnehmer)
    ahv_iv_nbu: float          # AHV/IV/NBU - 5.05% (2024)
    alv: float                 # ALV - 1.1% (2024)
    alv_zusatz: float          # ALV Zusatz - 0.5% für > CHF 148'200/Jahr (2024)
    
    # Weitere Abzüge
    krankenkasse: float        # Durchschnittliche Krankenkasse (Variable, hier Standard)
    pensionskasse: float       # 2. Säule Beitrag Arbeitnehmer
    
    # Steuerschätzung (grob)
    income_tax: float          # Geschätzte Einkommenssteuer
    
    # Summen
    total_employee_deductions: float
    net_monthly_income: float
    
    # Arbeitgeber-Anteile (informativ)
    employer_ahv_iv_nbu: float
    employer_alv: float
    employer_pensionskasse: float


class DeductionsCalculator:
    """Berechnet Schweizer Lohnabzüge"""
    
    # Konstanten aus config.py
    AHV_IV_NBU_RATE = config.AHV_IV_NBU_RATE
    ALV_RATE = config.ALV_RATE
    ALV_ZUSATZ_RATE = config.ALV_ZUSATZ_RATE
    ALV_ZUSATZ_THRESHOLD = config.ALV_ZUSATZ_THRESHOLD
    
    def __init__(self, 
                 gross_monthly_income: float,
                 employee_pillar2_contribution: float = 0,
                 annual_net_income_estimate: float = None,
                 canton: str = "ZH",
                 avg_health_insurance: float = 350):
        """
        Initialize Deductions Calculator
        
        Args:
            gross_monthly_income: Bruttolohn pro Monat in CHF
            employee_pillar2_contribution: Arbeitnehmer-Beitrag 2. Säule in CHF/Monat
            annual_net_income_estimate: Geschätztes Nettojahreseinkommen für Steuern
            canton: Kanton für Steuerschätzung (Standard: ZH)
            avg_health_insurance: Durchschn. Krankenkassenprämie/Monat (Standard: 350 CHF)
        """
        self.gross_monthly_income = gross_monthly_income
        self.gross_annual_income = gross_monthly_income * 12
        self.employee_pillar2_contribution = employee_pillar2_contribution
        self.canton = canton
        self.avg_health_insurance = avg_health_insurance
    
    def calculate(self) -> SalaryDeductions:
        """
        Berechne alle Lohnabzüge
        
        Returns:
            SalaryDeductions mit detaillierten Angaben
        """
        # Obligatorische Beiträge (prozentual auf Bruttolohn)
        ahv_iv_nbu = self.gross_monthly_income * self.AHV_IV_NBU_RATE
        alv = self.gross_monthly_income * self.ALV_RATE
        
        # ALV Zusatz (nur wenn Jahreseinkommen > Grenzwert)
        alv_zusatz = 0
        if self.gross_annual_income > self.ALV_ZUSATZ_THRESHOLD:
            alv_zusatz = self.gross_monthly_income * self.ALV_ZUSATZ_RATE
        
        # Krankenkasse (durchschnittlich, wird vom Versicherten bezahlt)
        krankenkasse = self.avg_health_insurance
        
        # 2. Säule Beitrag (vom Arbeitnehmer)
        pensionskasse = self.employee_pillar2_contribution
        
        # Geschätzte Einkommenssteuer (vereinfacht)
        # Schweizer Durchschnittssteuersatz ca. 15-20% je nach Kanton/Gemeinde
        # Hier eine grobe Schätzung
        income_tax = self._estimate_income_tax()
        
        # Summe Abzüge
        total_deductions = ahv_iv_nbu + alv + alv_zusatz + krankenkasse + pensionskasse + income_tax
        
        # Nettolohn
        net_monthly = self.gross_monthly_income - total_deductions
        
        # Arbeitgeber-Anteile (informativ)
        employer_ahv_iv_nbu = self.gross_monthly_income * self.AHV_IV_NBU_RATE
        employer_alv = self.gross_monthly_income * self.ALV_RATE
        employer_alv_zusatz = 0
        if self.gross_annual_income > self.ALV_ZUSATZ_THRESHOLD:
            employer_alv_zusatz = self.gross_monthly_income * self.ALV_ZUSATZ_RATE
        
        return SalaryDeductions(
            gross_monthly_income=self.gross_monthly_income,
            ahv_iv_nbu=ahv_iv_nbu,
            alv=alv,
            alv_zusatz=alv_zusatz,
            krankenkasse=krankenkasse,
            pensionskasse=pensionskasse,
            income_tax=income_tax,
            total_employee_deductions=total_deductions,
            net_monthly_income=net_monthly,
            employer_ahv_iv_nbu=employer_ahv_iv_nbu,
            employer_alv=employer_alv,
            employer_pensionskasse=self.employee_pillar2_contribution,
        )
    
    def _estimate_income_tax(self) -> float:
        """
        Grobe Schätzung der Einkommenssteuer
        
        Returns:
            Geschätzte monatliche Steuer in CHF
        """
        # Steuersätze aus config
        rate = config.get_canton_tax_rate(self.canton)
        
        # Vereinfachter Freibetrag aus config
        annual_taxable_income = max(0, self.gross_annual_income - config.ANNUAL_TAX_ALLOWANCE)
        
        annual_tax = annual_taxable_income * rate
        monthly_tax = annual_tax / 12
        
        return monthly_tax
    
    def get_summary(self) -> Dict:
        """Erstelle Summary der Lohnabzüge"""
        result = self.calculate()
        
        return {
            'gross_monthly': result.gross_monthly_income,
            'gross_annual': self.gross_annual_income,
            'net_monthly': result.net_monthly_income,
            'net_annual': result.net_monthly_income * 12,
            'deductions': {
                'ahv_iv_nbu': result.ahv_iv_nbu,
                'alv': result.alv,
                'alv_zusatz': result.alv_zusatz,
                'krankenkasse': result.krankenkasse,
                'pensionskasse': result.pensionskasse,
                'income_tax': result.income_tax,
            },
            'total_deductions': result.total_employee_deductions,
            'net_rate': result.net_monthly_income / result.gross_monthly_income,
        }
