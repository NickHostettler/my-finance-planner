# Swiss Personal Finance Planning Tool

Ein Python-Paket für private Finanzplanung nach dem Schweizer Rentensystem (1., 2. und 3. Säule).

## Features

- **Nettolohn Input**: Einfache Eingabe des monatlichen Nettolohns
- **2. Säule Berechnung**: Automatische Berechnung des Berufsvorsorgeanspruchs (BVG-konform)
- **3a Szenarien**: Mehrere Sparlösungen für die 3. Säule
- **Sparquote & Beträge**: Konfigurierbare Sparquoten oder feste monatliche Sparraten
- **Dash Dashboard**: Interaktive Visualisierung und Vermögensanalyse
- **Live-Planung**: Monatliches oder jährliches Brutto-/Nettoeinkommen, flexible 3a/3b-Beiträge und Renditeannahmen mit interaktiven Prognosegrafiken; Brutto wird anhand des gewählten Kantons vereinfacht netto geschätzt
- **2. Säule**: Vereinfachtes BVG-Schätzmodell (keine offizielle Mindestberechnung) oder eigene monatliche Arbeitnehmer-/Arbeitgeberbeiträge und PK-Verzinsung
- **Startguthaben**: Bereits vorhandene Guthaben in der 2. Säule, 3a und 3b fliessen in die Projektion ein
- **Transparente Modellannahmen**: Renditen, nominale Werte ohne Inflationsbereinigung, Vereinfachungen der BVG-Schätzung und nicht berücksichtigte Faktoren werden bei der Prognose ausgewiesen
- **Nominale und reale Prognose**: Umschaltbare Anzeige in zukünftigen CHF oder kaufkraftbereinigten heutigen CHF unter Verwendung der konfigurierten jährlichen Inflation
- **AHV-Rente**: Unverbindliche Schätzung anhand des durchschnittlichen Jahreseinkommens und der Beitragsjahre als separates Ruhestandseinkommen; 13 Jahreszahlungen sind berücksichtigt, die AHV wird nicht zum Vorsorgekapital addiert
- **Lokale Szenarien**: Dashboard-Eingaben lassen sich benannt in einer lokalen SQLite-Datenbank speichern, laden und löschen; ein erneut gespeicherter Name aktualisiert das bestehende Szenario
- **Zukunftsprognose**: Szenarioanalyse über einen konfigurierbaren Zeithorizont

## Installation

```bash
uv sync
```

## Verwendung

### Als CLI Dashboard starten:

```bash
uv run swiss-finance-dashboard
```

Das Dashboard öffnet sich dann unter `http://localhost:8050`

Gespeicherte Szenarien und deine zuletzt verwendeten Dashboard-Eingaben enthalten die Werte als SQL-Spalten. Unter Windows
liegt die Datenbank standardmässig unter `%LOCALAPPDATA%\SwissFinanceDashboard\scenarios.sqlite3`
(andere Betriebssysteme verwenden das jeweilige Benutzer-Datenverzeichnis). Sie bleibt ausserhalb
des Projektordners, wird nicht verschlüsselt und sollte nicht ungeschützt weitergegeben werden.
Die zuletzt eingegebenen Werte werden automatisch gespeichert und beim nächsten Dashboard-Start
wiederhergestellt; sie sind unabhängig von benannten Szenarien.

### AHV-Rentenschätzung

Im Dashboard gibst du das massgebende durchschnittliche Jahreseinkommen und die erwarteten
Beitragsjahre ein. Die unverbindliche Schätzung interpoliert vereinfacht zwischen der Mindest- und Maximalrente der
Vollrentenskala 44 und berücksichtigt die eingegebenen Beitragsjahre anteilig. Sie bildet die
offizielle Rententabelle nicht nach und berücksichtigt unter anderem keine individuellen IK-Daten,
Erziehungs- oder Betreuungsgutschriften, Einkommensteilung oder Übergangsregeln. Nutze für deine
Planung die Schätzung daher nur als grobe Orientierung.

Die geschätzte Rente wird getrennt vom projizierten Vorsorgekapital angezeigt und enthält 13
Jahreszahlungen. Im Nominalmodus wird die Schätzung in heutigen CHF modellhaft mit der hinterlegten
Inflation hochgerechnet; in der Realansicht bleibt sie in heutiger Kaufkraft. Die effektive
künftige Rentenanpassung kann davon abweichen. Steuern auf Renten sind nicht berücksichtigt.

Quellen: [AHV-Merkblatt 3.01](https://www.ahv-iv.ch/p/3.01.d) und
[Information zur 13. AHV-Rente](https://www.ahv-iv.ch/de/Sozialversicherungen/Alters-und-Hinterlassenenversicherung-AHV/13-AHV-Rente).

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
- 3a (gebundene Vorsorge): Das Modell begrenzt die Einzahlung auf maximal CHF 7'258 pro Jahr (ca. CHF 604.83 pro Monat)
- 3b (freie Vorsorge): Ohne Limit

## Development

Tests ausführen:
```bash
uv run pytest
```

Mit Coverage:
```bash
uv run pytest --cov=personal_finance
```

```bash
uv run ruff check .
```

## License

MIT
