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
- **Szenarien im eigenen Browser**: Dashboard-Eingaben lassen sich benannt speichern, laden und löschen; ein erneut gespeicherter Name aktualisiert das bestehende Szenario. Die Daten bleiben im Browser des Nutzers, der Server speichert nichts
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

Das Dashboard öffnet sich automatisch im Standardbrowser unter `http://127.0.0.1:8050`,
sobald der Server bereit ist. Optionen:

```bash
uv run swiss-finance-dashboard --no-browser   # Browser nicht öffnen
uv run swiss-finance-dashboard --port 8080    # anderer Port
uv run swiss-finance-dashboard --debug        # Auto-Reload bei Codeänderungen (öffnet nur einen Tab)
```

`python -m personal_finance` akzeptiert dieselben Optionen.

### Produktionsbetrieb (Server/Container)

Auf einem Server läuft die App mit [gunicorn](https://gunicorn.org/) statt mit dem
Dash-Entwicklungsserver. gunicorn läuft nur unter Linux/macOS, also z.B. im Docker-Container,
und wird unter Windows nicht installiert.

```bash
gunicorn -c python:personal_finance.gunicorn_conf personal_finance.wsgi:server
```

| Umgebungsvariable | Standard | Bedeutung |
|---|---|---|
| `PORT` | `8050` | Port (setzen Hoster wie Render automatisch) |
| `HOST` | `0.0.0.0` | Interface |
| `WEB_CONCURRENCY` | `2` | Worker-Prozesse |
| `GUNICORN_THREADS` | `4` | Threads pro Worker |
| `LOG_LEVEL` | `info` | Log-Level |
| `APP_PASSWORD` | – | Gemeinsames Passwort (mind. 12 Zeichen); aktiviert den Login |
| `APP_USERNAME` | `kamerad` | Benutzername für den Login |
| `REQUIRE_AUTH` | `1` im Docker-Image | Start ohne `APP_PASSWORD` wird verweigert |

- `GET /health` antwortet mit `200 {"status": "ok"}` für die Health-Checks der Plattform.
- Der Debug-Modus ist im Produktionsbetrieb nie aktiv, und der Browser wird nicht geöffnet.
- Die Logs enthalten keine Eingabewerte und keine Client-IP-Adressen.

### Zugriffsschutz (Passwort)

Ist `APP_PASSWORD` gesetzt, fragt der Browser beim Öffnen nach Benutzername und Passwort
(HTTP Basic Auth über HTTPS). Öffentlich bleiben nur `/health` (für die Plattform) und
`/robots.txt`. Zusätzlich verbieten `robots.txt` und der Header `X-Robots-Tag` Suchmaschinen
das Indexieren.

- **Das Docker-Image startet nie ohne Passwort** (`REQUIRE_AUTH=1`). So kann die App nicht
  versehentlich offen online gehen. Lokal mit `uv run swiss-finance-dashboard` ist kein
  Passwort nötig; die App ist dort nur auf deinem Rechner erreichbar.
- Ein sicheres Passwort erzeugen:
  ```bash
  uv run python -c "import secrets; print(secrets.token_urlsafe(18))"
  ```
- Das Passwort gehört **nur** in die Umgebungsvariablen bzw. Secrets der Hosting-Plattform,
  nie ins Repository.
- Das Passwort hält Fremde fern, **trennt aber nicht zwischen den Kameraden**. Diese Trennung
  entsteht dadurch, dass die Daten nur im eigenen Browser liegen (siehe unten).
- Basic Auth hat kein „Abmelden“: Der Browser merkt sich den Login, bis er geschlossen wird.
  Auf fremden Geräten deshalb ein privates Fenster nutzen.

### Mit Docker starten

Das [`Dockerfile`](Dockerfile) baut ein schlankes Produktions-Image: Python-Version aus
`.python-version`, Abhängigkeiten exakt aus `uv.lock`, gunicorn, eigener Benutzer ohne
root-Rechte und ein eingebauter `HEALTHCHECK`. Mit Docker Desktop lokal testen:

```powershell
$env:APP_PASSWORD = "ein-langes-test-passwort"
docker compose up --build        # -> http://localhost:8050  (Login: kamerad / Passwort)
```

oder ohne Compose:

```bash
docker build -t my-finance-planner .
docker run --rm -p 8050:8050 -e APP_PASSWORD="ein-langes-test-passwort" my-finance-planner
```

Der Container kommt mit schreibgeschütztem Dateisystem aus (`read_only` in
[`compose.yaml`](compose.yaml)), weil die App keine Daten auf dem Server speichert. Die CI baut
das Image bei jedem PR und prüft es auf diese Weise, inklusive Login und der Weigerung, ohne
Passwort zu starten.

### Wo werden meine Daten gespeichert?

Gespeicherte Szenarien und die zuletzt verwendeten Eingaben liegen **ausschliesslich im
`localStorage` deines Browsers** (Schlüssel `pf-scenarios` und `pf-last-inputs`). Der Server
rechnet nur. Er schreibt nichts auf die Festplatte, hält nichts im Speicher und loggt keine
Eingaben. Dadurch gilt:

- Jeder Nutzer sieht nur seine eigenen Daten, auch wenn alle denselben Server verwenden.
- Ein Neustart oder Deploy des Servers löscht keine Nutzerdaten.
- Die Daten sind an Gerät und Browserprofil gebunden. Wer dasselbe Profil nutzt, sieht sie.
  Löschen kannst du sie über „Löschen“ in der App oder die Websitedaten des Browsers.
- Die Daten werden im Browser nicht verschlüsselt.

Die letzten Eingaben werden automatisch gemerkt und beim nächsten Öffnen wiederhergestellt; sie
sind unabhängig von benannten Szenarien.

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
src/personal_finance/
├── __init__.py            # Öffentliche API (FinanceCalculator)
├── __main__.py            # python -m personal_finance → startet das Dashboard
├── config.py              # Zentrale Konstanten (BVG, 3a-Limit, Kantone, …)
├── calculator.py          # Fassade: kombiniert alle Berechnungen
├── wsgi.py                # Einstiegspunkt für gunicorn (Produktion)
├── gunicorn_conf.py       # gunicorn-Einstellungen aus Umgebungsvariablen
├── core/                  # Reine Fachlogik – keine Abhängigkeit zu Dash/Storage
│   ├── ahv.py             # AHV-Rentenschätzung
│   ├── deductions.py      # Lohnabzüge Brutto → Netto
│   ├── income.py          # Einkommen normalisieren (Monat/Jahr, Brutto/Netto)
│   ├── pillar_2.py        # 2. Säule (BVG)
│   ├── pillar_3a.py       # 3a (gebundene Vorsorge)
│   ├── pillar_3b.py       # 3b (freie Vorsorge)
│   ├── projection.py      # Zinseszins-Projektion
│   └── savings.py         # Sparquote / Sparbetrag
├── storage/
│   └── browser_store.py   # Szenarien im Browser (reine Funktionen, kein Server-Speicher)
└── dashboard/             # Dash-UI
    ├── __init__.py        # Verdrahtung: Layout + Callbacks, run_dashboard()
    ├── app.py             # Dash-Instanz + /health
    ├── auth.py            # Passwortschutz (Basic Auth) + robots.txt
    ├── layout.py          # Seitenaufbau
    ├── components.py      # Wiederverwendbare UI-Bausteine
    ├── figures.py         # Plotly-Grafiken
    ├── results.py         # Ergebnisbereich
    ├── callbacks.py       # Interaktionen
    ├── theme.py           # Farben
    └── assets/            # CSS (wird von Dash automatisch geladen)

tests/
├── unit/                  # Fachlogik
└── ui/                    # Dashboard-Layout & Callbacks

examples/                  # Beispielskripte
docs/                      # Weitere Dokumentation (Installation)
```

Abhängigkeiten zeigen nur nach innen: `dashboard` → `storage`/`calculator` → `core` → `config`.

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
uv run pytest --cov
```

Nur eine Testebene:
```bash
uv run pytest tests/unit
```

Browser-Tests (End-to-End, prüfen u.a., dass Nutzer die Daten anderer nicht sehen):
```bash
uv sync --group e2e
uv run playwright install chromium     # oder vorhandenen Edge nutzen:
$env:E2E_BROWSER_CHANNEL="msedge"      # (PowerShell)
uv run pytest tests/e2e
```
Ohne Playwright werden diese Tests automatisch übersprungen.

### CI

Jeder Pull Request und jeder Push auf `main` startet [GitHub Actions](.github/workflows/ci.yml):

- **Lint & Tests** auf Linux (Produktionsplattform, inkl. echtem gunicorn-Start) und Windows
- **Browser-Test** mit Chromium (Nutzer-Isolation)
- **Docker-Build** mit Health-Check, sobald ein `Dockerfile` existiert

```bash
uv run ruff check .
```

## License

MIT
