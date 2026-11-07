"""
Configuration Module - Zentrale Konstanten und Settings

Alle hardcodierten Werte für die Finanzberechnungen sind hier zentral definiert.
So können Werte einfach angepasst werden (z.B. für neue Gesetze oder Jahre).
"""

# ================================================================================
# INFLATION UND RENDITE (Default-Annahmen)
# ================================================================================

ASSUMED_ANNUAL_RETURN = 0.04  # 4% angenommene jährliche Rendite
INFLATION_RATE = 0.02  # 2% angenommene jährliche Inflation

# ================================================================================
# 2. SÄULE (BVG - Berufliche Vorsorge)
# ================================================================================

PILLAR2_MIN_SALARY = 24885  # CHF - Mindestlohn für BVG-Versicherung (2024)
PILLAR2_COORDINATION_DEDUCTION = 24885  # CHF - Koordinationsabzug
PILLAR2_MAX_CONTRIBUTION_RATE = 0.15  # Max. 15% Beitragssatz

# Altersabhängige Beitragssätze (kombiniert Arbeitgeber + Arbeitnehmer)
PILLAR2_CONTRIBUTION_RATES = {
    'age_under_25': 0.07,      # 7%
    'age_25_34': 0.10,         # 10%
    'age_35_44': 0.12,         # 12%
    'age_45_54': 0.14,         # 14%
    'age_55_plus': 0.15,       # 15%
}

# ================================================================================
# 3. SÄULE 3a (Gebundene Vorsorge - mit Steuervorteilen)
# ================================================================================

PILLAR3A_ANNUAL_MAX = 7258  # CHF - Maximale jährliche 3a Einzahlung
PILLAR3A_MONTHLY_MAX = PILLAR3A_ANNUAL_MAX / 12

# ================================================================================
# 3. SÄULE 3b (Freie Vorsorge - unbegrenzt)
# ================================================================================

# 3b hat keine Limits - vordefinierte Szenarien sind nur Empfehlungen

# ================================================================================
# SCHWEIZER LOHNABZÜGE (Deductions)
# ================================================================================

# AHV/IV/NBU - Alters- und Hinterlassenenversicherung, etc.
AHV_IV_NBU_RATE = 0.0505  # 5.05% (2024)
AHV_IV_NBU_RATE_EMPLOYER = 0.0505  # 5.05% (2024)

# ALV - Arbeitslosenversicherung
ALV_RATE = 0.011  # 1.1% (2024)
ALV_RATE_EMPLOYER = 0.011  # 1.1% (2024)

# ALV Zusatz (über CHF 148'200 Jahreseinkommen)
ALV_ZUSATZ_RATE = 0.005  # 0.5% (2024)
ALV_ZUSATZ_THRESHOLD = 148200  # CHF

# Krankenkassenprämie (durchschnittliche Schätzung)
AVERAGE_HEALTH_INSURANCE_MONTHLY = 350  # CHF

# Kantonal unterschiedliche Steuersätze (Schätzung: Bundessteuer + durchschn. Kantons-/Gemeindesteuern)
CANTON_TAX_RATES = {
    'ZH': 0.165,  # Zürich
    'BE': 0.145,  # Bern
    'LU': 0.155,  # Luzern
    'BS': 0.175,  # Basel-Stadt
    'BL': 0.165,  # Basel-Landschaft
    'AG': 0.140,  # Aargau
    'SO': 0.150,  # Solothurn
    'SG': 0.155,  # St. Gallen
    'AR': 0.160,  # Appenzell Ausserrhoden
    'AI': 0.150,  # Appenzell Innerrhoden
    'GE': 0.145,  # Genf
    'VD': 0.140,  # Waadt
    'VS': 0.140,  # Wallis
    'NE': 0.150,  # Neuenburg
    'JU': 0.150,  # Jura
    'TI': 0.150,  # Tessin
    'GR': 0.155,  # Graubünden
    'UR': 0.145,  # Uri
    'OW': 0.145,  # Obwalden
    'NW': 0.150,  # Nidwalden
    'GL': 0.150,  # Glarus
    'SH': 0.145,  # Schaffhausen
    'TG': 0.150,  # Thurgau
    'FR': 0.150,  # Freiburg
}

# Freibetrag für Steuerberechnung (vereinfacht)
ANNUAL_TAX_ALLOWANCE = 15000  # CHF

# ================================================================================
# RENTENSYSTEM-PARAMETER
# ================================================================================

DEFAULT_RETIREMENT_AGE = 65  # Pensionierungsalter (Standard)
MIN_RETIREMENT_AGE = 55  # Minimal mögliches Renteneintrittsalter
MAX_RETIREMENT_AGE = 75  # Maximal betrachtetes Renteneintrittsalter

# ================================================================================
# VALIDIERUNGS-GRENZEN
# ================================================================================

# Warnung bei zu niedriger Sparquote
MIN_RECOMMENDED_SAVINGS_RATE = 0.05  # 5%

# Warnung bei zu hoher Sparquote
MAX_RECOMMENDED_SAVINGS_RATE = 0.25  # 25%

# ================================================================================
# UTILITY FUNKTIONEN ZUM ABRUFEN VON KONFIGURATIONEN
# ================================================================================

def get_pillar2_contribution_rate(current_age: int) -> float:
    """
    Ermittle den altersabhängigen 2. Säule Beitragssatz
    
    Args:
        current_age: Aktuelles Alter
    
    Returns:
        Beitragssatz als Dezimal (z.B. 0.10 = 10%)
    """
    if current_age < 25:
        return PILLAR2_CONTRIBUTION_RATES['age_under_25']
    elif current_age < 35:
        return PILLAR2_CONTRIBUTION_RATES['age_25_34']
    elif current_age < 45:
        return PILLAR2_CONTRIBUTION_RATES['age_35_44']
    elif current_age < 55:
        return PILLAR2_CONTRIBUTION_RATES['age_45_54']
    else:
        return PILLAR2_CONTRIBUTION_RATES['age_55_plus']


def get_canton_tax_rate(canton: str) -> float:
    """
    Ermittle den Steuersatz für einen Kanton
    
    Args:
        canton: Kantons-Abkürzung (z.B. 'ZH', 'BE')
    
    Returns:
        Steuersatz als Dezimal (z.B. 0.165 = 16.5%)
    """
    return CANTON_TAX_RATES.get(canton, 0.15)  # Default: 15%


def validate_pillar3a_amount(annual_amount: float) -> bool:
    """
    Validiere, ob 3a-Betrag im Limit liegt
    
    Args:
        annual_amount: Jährlicher 3a-Betrag in CHF
    
    Returns:
        True wenn ok, False wenn über Limit
    """
    return annual_amount <= PILLAR3A_ANNUAL_MAX


# ================================================================================
# VERSION UND METADATA
# ================================================================================

CONFIG_VERSION = "2024.1"  # Format: YEAR.REVISION
LAST_UPDATED = "2024-01-24"
