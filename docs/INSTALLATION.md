# Installation & Setup Guide

## Voraussetzungen

- Python 3.9 oder höher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python-Paket- und Projektmanager)

## Installation

### 1. Repository klonen oder Verzeichnis nutzen

```bash
cd c:\Users\nickh\github_repos\tool
```

### 2. Package installieren

```bash
uv sync
```

Dies installiert das Paket im Development-Modus mit allen Abhängigkeiten:
- pandas
- numpy
- dash & plotly (für Dashboard)
- python-dateutil

### 3. Entwicklungs-Tools

Die Entwicklungsgruppe wird von `uv sync` standardmässig mitinstalliert. Sie enthält zusätzlich:

- pytest & pytest-cov
- Ruff (schneller Linter; enthält optional auch einen Formatter)
- mypy (Type Checker)

## Erste Schritte

### Option 1: Beispiel-Script ausführen

```bash
uv run python examples/example_usage.py
```

Dies zeigt ein vollständiges Beispiel mit:
- 2. Säule Berechnung
- 3a Sparlösungen (verschiedene Szenarien)
- Empfehlungen

### Option 2: Interaktives Dash Dashboard starten

```bash
uv run swiss-finance-dashboard
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
uv run pytest

# Mit Coverage-Report
uv run pytest --cov

# Spezifisch eine Test-Datei
uv run pytest tests/unit/test_calculator.py -v

# Linting
uv run ruff check .
```

## Projektstruktur

Siehe [README.md](../README.md#projektstruktur).

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
- Max. CHF 7'258/Jahr für 3a (gebundene Vorsorge; ca. CHF 604.83/Monat)
- Oder 20% des Nettoeinkommens (je kleiner)

### Q: Wie wird die Kapitalrendite berechnet?
A: Verwendet Compound Interest (Zinseszins). Standard ist 4% jährlich.

### Q: Kann ich das für mehrere Szenarien nutzen?
A: Ja, erstellen Sie einfach mehrere `FinanceCalculator` Instanzen mit unterschiedlichen Parametern.

## Troubleshooting

### "ModuleNotFoundError: No module named 'personal_finance'"

Stellen Sie sicher, dass Sie im korrekten Verzeichnis sind und die Umgebung synchronisiert haben:

```bash
cd c:\Users\nickh\github_repos\tool
uv sync
```

### Dashboard startet nicht

Überprüfen Sie, ob Port 8050 frei ist:

```bash
# Windows
netstat -ano | findstr :8050

# Oder einen anderen Port nutzen:
uv run python -c "from personal_finance.dashboard import run_dashboard; run_dashboard(port=8080)"
```

### ImportError bei pandas/numpy

Synchronisieren Sie die Abhängigkeiten:

```bash
uv sync
```

## Support

Für weitere Informationen siehe [README.md](../README.md)
