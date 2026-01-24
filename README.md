# Swiss Personal Finance Planning Tool

Ein Python-Paket für private Finanzplanung nach dem Schweizer Rentensystem (1., 2. und 3. Säule).

## Features

- **Nettolohn Input**: Einfache Eingabe des monatlichen Nettolohns
- **2. Säule Berechnung**: Automatische Berechnung des Berufsvorsorgeanspruchs (BVG-konform)
- **3a Szenarien**: Mehrere Sparlösungen für die 3. Säule
- **Sparquote & Beträge**: Konfigurierbare Sparquoten oder feste monatliche Sparraten
- **Dash Dashboard**: Interaktive Visualisierung und Vermögensanalyse
- **Zukunftsprognose**: Szenarioanalyse über einen konfigurierbaren Zeithorizont

## Installation

```bash
pip install -e .
```

Oder mit Entwicklungs-Dependencies:

```bash
pip install -e ".[dev]"
```

## Verwendung

### Als CLI Dashboard starten:

```bash
swiss-finance-dashboard
```

Das Dashboard öffnet sich dann unter `http://localhost:8050`

### Programmatisch:

```python
from personal_finance.calculator import FinanceCalculator

# Initialisiere den Calculator
calc = FinanceCalculator(
    monthly_net_income=5000,  # CHF
    current_age=35,
    retirement_age=65,
)

# Berechne 2. Säule
pillar2 = calc.calculate_pillar2()
print(f"2. Säule Anspruch: {pillar2['annual_contribution']:.2f} CHF")

# Berechne 3a Szenario mit 10% Sparquote
pillar3a_scenario1 = calc.calculate_pillar3a(savings_rate=0.10)
print(f"3a Szenario 1 (10% Sparquote): {pillar3a_scenario1['total_at_retirement']:.2f} CHF")

# Berechne 3a mit festem monatlichem Betrag
pillar3a_scenario2 = calc.calculate_pillar3a(monthly_amount=1000)
print(f"3a Szenario 2 (1000 CHF/Monat): {pillar3a_scenario2['total_at_retirement']:.2f} CHF")

# Gesamtanalyse
analysis = calc.complete_analysis()
```

## Projektstruktur

```
personal_finance/
├── __init__.py
├── calculator.py          # Hauptklasse für Berechnungen
├── pillar_2.py           # 2. Säule (Berufvorsorge) Module
├── pillar_3a.py          # 3a Sparlösungen Module
├── savings.py            # Sparquote und Betrag Berechnungen
└── dashboard.py          # Dash Dashboard Anwendung

tests/
├── test_pillar2.py
├── test_pillar3a.py
└── test_calculator.py
```

## Konfiguration

Die meisten Parameter können über die `FinanceCalculator` Klasse konfiguriert werden:

- **monthly_net_income**: Monatlicher Nettolohn in CHF
- **current_age**: Aktuelles Alter
- **retirement_age**: Pensionierungsalter (Standard: 65)
- **assumed_return**: Angenommene jährliche Kapitalrendite (Standard: 0.04 = 4%)
- **inflation_rate**: Jährliche Inflationsrate (Standard: 0.02 = 2%)

## Notes zur Schweizer Finanzplanung

### 2. Säule (BVG)
- Minimal: Mindestbeitrag ab CHF 24,885 pro Jahr (50/50 Arbeitgeber/Arbeitnehmer)
- AHV-Renteneintrittsalter ist maßgeblich
- Koordinationsabzug beachten

### 3. Säule
- 3a (gebundene Vorsorge): Max. 7'056 CHF/Jahr (2024) oder 20% des Nettoeinkommens
- 3b (freie Vorsorge): Ohne Limit

## Development

Tests ausführen:
```bash
pytest
```

Mit Coverage:
```bash
pytest --cov=personal_finance
```

Code formatieren:
```bash
black personal_finance tests
```

## License

MIT
