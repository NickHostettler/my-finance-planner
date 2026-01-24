# Installation & Setup Guide

## Voraussetzungen

- Python 3.9 oder höher
- pip (Python Package Manager)

## Installation

### 1. Repository klonen oder Verzeichnis nutzen

```bash
cd c:\Users\nickh\github_repos\tool
```

### 2. Package installieren

```bash
pip install -e .
```

Dies installiert das Paket im Development-Modus mit allen Abhängigkeiten:
- pandas
- numpy
- dash & plotly (für Dashboard)
- python-dateutil

### 3. (Optional) Entwicklungs-Tools installieren

Für Testing und Code Quality:

```bash
pip install -e ".[dev]"
```

Dies installiert zusätzlich:
- pytest & pytest-cov
- black (Code Formatter)
- flake8 (Linter)
- mypy (Type Checker)

## Erste Schritte

### Option 1: Beispiel-Script ausführen

```bash
python example_usage.py
```

Dies zeigt ein vollständiges Beispiel mit:
- 2. Säule Berechnung
- 3a Sparlösungen (verschiedene Szenarien)
- Empfehlungen

### Option 2: Interaktives Dash Dashboard starten

```bash
swiss-finance-dashboard
```

Das Dashboard öffnet sich dann unter: **http://localhost:8050**

Im Dashboard können Sie:
- Nettolohn eingeben
- Alter und Pensionierungsalter setzen
- 3a Sparquote oder monatlichen Betrag definieren
- Interaktive Grafiken und Prognosen sehen

### Option 3: Programmatisch nutzen

```python
from personal_finance.calculator import FinanceCalculator

# Initialize
calc = FinanceCalculator(
    monthly_net_income=5000,  # CHF
    current_age=35,
    retirement_age=65,
)

# Calculate pillar 2
pillar2 = calc.calculate_pillar2()
print(f"2. Säule monatlich: {pillar2.annual_contribution_total / 12:.2f} CHF")

# Calculate pillar 3a with 10% savings rate
pillar3a = calc.calculate_pillar3a(savings_rate=0.10)
print(f"3a bei Pensionierung: {pillar3a.total_at_retirement:.0f} CHF")

# Get complete analysis with recommendations
analysis = calc.complete_analysis()
for rec in analysis.summary['recommendations']:
    print(f"- {rec}")
```

## Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage-Report
pytest --cov=personal_finance

# Spezifisch eine Test-Datei
pytest tests/test_calculator.py -v
```

## Projektstruktur

```
personal_finance/
├── __init__.py                 # Package init
├── calculator.py              # Haupt-Calculator Klasse
├── pillar_2.py               # 2. Säule (BVG) Module
├── pillar_3a.py              # 3a Sparlösungen Module
├── savings.py                # Sparquote/Betrag Verwaltung
└── dashboard.py              # Dash Dashboard App

tests/
├── __init__.py
└── test_calculator.py        # Unit Tests

example_usage.py              # Beispiel-Script
pyproject.toml               # Package Konfiguration
README.md                    # Dokumentation
```

## Konfiguration

### Dashboard-Port ändern

Um den Dashboard auf einem anderen Port zu starten (Standard: 8050):

```bash
# In Python
from personal_finance.dashboard import run_dashboard
run_dashboard(port=8080)
```

### Berechnungsparameter anpassen

```python
calc = FinanceCalculator(
    monthly_net_income=8000,
    current_age=29,
    retirement_age=65,
    assumed_annual_return=0.10,  # 4% angenommene Rendite
    inflation_rate=0.02,         # 2% Inflation
)
```

## Häufig gestellte Fragen

### Q: Welche Versicherungsmindestlöhne sind berücksichtigt?
A: Die 2. Säule berechnet sich nach BVG. Das Modell verwendet CHF 24'885 als Koordinationsabzug (2024 Wert).

### Q: Sind die 3a Limits realistisch?
A: Ja, das Modell beachtet die 2024er Limits:
- Max. CHF 7'056/Jahr für 3a (gebundene Vorsorge)
- Oder 20% des Nettoeinkommens (je kleiner)

### Q: Wie wird die Kapitalrendite berechnet?
A: Verwendet Compound Interest (Zinseszins). Standard ist 4% jährlich.

### Q: Kann ich das für mehrere Szenarien nutzen?
A: Ja, erstellen Sie einfach mehrere `FinanceCalculator` Instanzen mit unterschiedlichen Parametern.

## Troubleshooting

### "ModuleNotFoundError: No module named 'personal_finance'"

Stellen Sie sicher, dass Sie im korrekten Verzeichnis sind und das Paket installiert haben:

```bash
cd c:\Users\nickh\github_repos\tool
pip install -e .
```

### Dashboard startet nicht

Überprüfen Sie, ob Port 8050 frei ist:

```bash
# Windows
netstat -ano | findstr :8050

# Oder einen anderen Port nutzen:
python -c "from personal_finance.dashboard import run_dashboard; run_dashboard(port=8080)"
```

### ImportError bei pandas/numpy

Installieren Sie die Abhängigkeiten:

```bash
pip install -e .
```

## Support

Für weitere Informationen siehe [README.md](README.md)
