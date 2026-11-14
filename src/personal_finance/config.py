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

# AHV/IV/EO - auf dem gesamten Lohn, ohne Obergrenze.
# Quelle: Merkblatt 2.01 "Lohnbeiträge an die AHV, die IV und die EO", Stand 1.1.2026
# (AHV 8.7% + IV 1.4% + EO 0.5% = 10.6%, je hälftig Arbeitnehmer/Arbeitgeber)
AHV_IV_EO_RATE = 0.053  # 5.3% Arbeitnehmer
AHV_IV_EO_RATE_EMPLOYER = 0.053  # 5.3% Arbeitgeber

# ALV - Arbeitslosenversicherung, nur bis zum Höchstlohn.
# Quelle: Merkblatt 2.08 "Beiträge an die Arbeitslosenversicherung", Stand 1.1.2025.
# Seit 1.1.2023 fällt auf Lohnanteilen über dem Höchstlohn kein ALV-Beitrag mehr an
# (der frühere Solidaritätsbeitrag wurde abgeschafft).
ALV_RATE = 0.011  # 1.1% Arbeitnehmer
ALV_RATE_EMPLOYER = 0.011  # 1.1% Arbeitgeber
ALV_MAX_INSURED_ANNUAL_SALARY = 148200  # CHF pro Jahr

# NBU - Nichtberufsunfallversicherung (UVG), in der Regel vom Arbeitnehmer getragen.
# Die Prämie legt jeder Versicherer je nach Branche/Betrieb selbst fest; der Satz ist eine
# MODELLANNAHME. Versichert ist der Lohn bis zum UVG-Höchstbetrag.
NBU_RATE = 0.01  # 1.0% Arbeitnehmer (Annahme)
UVG_MAX_INSURED_ANNUAL_SALARY = 148200  # CHF pro Jahr

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
# WOHNEIGENTUM (Tragbarkeit und Eigenmittel, Stand November 2026)
# ================================================================================
# Das Modell setzt den Belehnungswert der Bank dem Kaufpreis gleich. Banken prüfen jeden
# Kauf individuell (Bonität, Objekt, eigene Sätze); die Werte sind keine Bankzusage.

# Verbindlich für alle Banken (von der FINMA als Mindeststandard anerkannt):
# SBVg "Richtlinien betreffend Mindestanforderungen bei Hypothekarfinanzierungen",
# Dezember 2023, gültig ab 1.1.2025.
HOME_SBVG_SOURCE_URL = (
    "https://www.finma.ch/de/news/2024/03/20240327-mm-hypothekarfinanzierungen/"
)
# Ziff. 2.1: Mindestens 10 % des Belehnungswerts müssen Eigenmittel sein, die nicht aus der
# 2. Säule stammen (weder Vorbezug noch Verpfändung). Erspartes, Wertschriften und Säule 3a
# zählen dazu ("harte" Eigenmittel).
HOME_MIN_HARD_EQUITY_RATE = 0.10
# Ziff. 2.2: Die Hypothekarschuld ist innert maximal 15 Jahren linear auf 2/3 des
# Belehnungswerts zu amortisieren (Amortisation der 2. Hypothek).
HOME_FIRST_MORTGAGE_MAX_RATE = 2 / 3
HOME_AMORTISATION_MAX_YEARS = 15

# Übliche Bankpraxis, keine gesetzliche Regel (die FINMA verlangt nur, dass Banken die
# Tragbarkeit vorsichtig prüfen). Einzelne Banken weichen davon ab:
HOME_MIN_EQUITY_RATE = 0.20  # mindestens 20 % Eigenmittel, Belehnung also höchstens 80 %
HOME_MAX_COST_TO_INCOME = 1 / 3  # Wohnkosten höchstens 1/3 des Bruttoeinkommens
HOME_IMPUTED_INTEREST_RATE = 0.05  # kalkulatorischer Zins (manche Banken: 4.5 %)
HOME_MAINTENANCE_RATE = 0.01  # Nebenkosten und Unterhalt pro Jahr, in % des Kaufpreises
# Zusätzlich verlangen Banken, dass die 2. Hypothek spätestens bei der Pensionierung
# amortisiert ist; das Modell verkürzt die Amortisationsdauer entsprechend.

# Modellannahmen dieses Tools:
# Kaufnebenkosten (Notar, Grundbuch, je nach Kanton Handänderungssteuer). Sie werden nicht
# finanziert und im Modell aus Erspartem oder 3a bezahlt; sie zählen nicht als Eigenmittel.
HOME_PURCHASE_COSTS_RATE = 0.03
# Ab diesem Anteil der Wohnkosten am Bruttoeinkommen gilt ein Kauf als "knapp" tragbar.
HOME_TIGHT_COST_TO_INCOME = 0.30

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


# ================================================================================
# VERSION UND METADATA
# ================================================================================

CONFIG_VERSION = "2024.1"  # Format: YEAR.REVISION
LAST_UPDATED = "2024-01-24"
