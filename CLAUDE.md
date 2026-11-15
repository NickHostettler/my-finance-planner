# CLAUDE.md

Schweizer Finanz- und Vorsorgeplaner: Python 3.14, Dash 4 mit Dash Mantine Components (DMC) 3,
Plotly, Paketverwaltung mit `uv`. Läuft als Docker-Container auf Render (siehe
`docs/DEPLOYMENT.md`). Code und Kommentare auf Englisch, alle Texte im UI und in der Doku auf
Deutsch in Schweizer Schreibweise („ss“ statt „ß“, Tausendertrennzeichen ’).

Weitere Regeln liegen dort, wo sie gelten, und werden beim Arbeiten im Ordner mitgeladen:

| Ordner | Inhalt |
|---|---|
| `src/personal_finance/core/CLAUDE.md` | Rechenkern: reine Funktionen, Regeln in `config.py` |
| `src/personal_finance/dashboard/CLAUDE.md` | Dash/Mantine-Stolperfallen, **Layout und Breiten** |
| `tests/CLAUDE.md` | Testaufbau, Coverage, e2e |

## Claude-Code-Struktur

```
CLAUDE.md                     dieses Dokument: Regeln, die überall gelten
src/…/core|dashboard/CLAUDE.md, tests/CLAUDE.md   Regeln pro Bereich (Tabelle oben)
.claude/
  settings.json               geteilt: Rechte, Schutz von .env, Format-Hook
  settings.local.json         persönlich, nicht im Repo
  hooks/format_python.py      formatiert jede bearbeitete .py-Datei mit ruff format
  skills/<name>/SKILL.md      wiederkehrende Abläufe
scripts/ui_check.py           Werkzeug für den Skill ui-check
```

| Skill | Wann |
|---|---|
| `ui-check` | nach jeder Änderung an Layout, CSS, Karten, Grafiken oder Tabs |
| `pr` | Arbeit als Pull Request gegen `main` abgeben |
| `release` | Meilenstein fertig: Version, Tag, GitHub-Release, Deploy |
| `jahreswerte` | Sätze und Grenzbeträge in `config.py` auf ein neues Jahr bringen |

Was wohin gehört:

- **CLAUDE.md:** kurze Regeln und Stolperfallen, die bei jeder Arbeit im Ordner gelten. Eine
  Regel für nur einen Bereich gehört in dessen CLAUDE.md, nicht hierher.
- **Skill:** ein Ablauf mit mehreren Schritten, der nur manchmal gebraucht wird. Ein neuer
  Skill lohnt sich, sobald derselbe Ablauf zum zweiten Mal erklärt werden müsste.
- **Hook / `settings.json`:** was immer und ohne Nachdenken passieren muss (Formatierung,
  Rechte). Hooks blockieren nie und ändern nur die gerade bearbeitete Datei.
- Bewusst nicht vorhanden: eigene Subagenten, MCP-Server, Plugins und `.claude/commands/`
  (Skills ersetzen Commands). Erst anlegen, wenn ein konkreter Bedarf da ist.
- Neue Erkenntnisse aus einer Sitzung (Stolperfalle, geänderter Ablauf) im selben PR in die
  passende CLAUDE.md oder den Skill nachtragen und Überholtes dort löschen.

## Aufbau

```
src/personal_finance/
  config.py      fachliche Konstanten mit Quellen (Lohnabzüge, BVG, 3a, Wohneigentum, WEF)
  core/          reine Fachlogik, ohne Dash
  storage/       browser_store: Szenarien und letzte Eingaben, nur im Browser
  dashboard/     layout.py (statisch), callbacks.py, results.py / home_view.py (Tabs)
tests/unit|ui|e2e
docs/            ANLEITUNG.md (Nutzer), DEPLOYMENT.md, INSTALLATION.md
```

## Befehle

```powershell
uv run ruff check .                          # Lint
uv run ruff format .                         # Formatierung; die CI prüft mit --check
uv run pytest -q --cov --ignore=tests/e2e   # 100 % Line- und Branch-Coverage sind Pflicht
uv run pytest tests/e2e                      # Browser-Tests; einmalig: uv sync --group e2e
                                             # und uv run playwright install chromium
uv run python -m personal_finance            # App lokal starten (öffnet den Browser)
```

Die Shell ist Windows PowerShell. `gh` ist evtl. nicht im PATH:
`& "C:\Program Files\GitHub CLI\gh.exe" ...`

## Arbeitsweise

- Jede Änderung auf einem eigenen Branch, dann Push und PR gegen `main`. PR-Beschreibung auf
  Deutsch (Zusammenfassung + Tests). Nie direkt auf `main` committen. `main` ist geschützt,
  das Repo ist öffentlich (nur zum Ansehen, proprietäre Lizenz).
- Grössere Aufgaben in kleinen, einzeln grünen Commits (`ruff check`, `ruff format`,
  Tests + Coverage).
- Render deployt automatisch, sobald `main` eine grüne CI hat.
- Nach UI-Änderungen den Skill `ui-check` laufen lassen, nicht nur die Unit-Tests.

## Datenschutz (nicht verhandelbar)

- Nutzerdaten bleiben **nur im Browser** (`dcc.Store(storage_type="local")`, Keys mit Präfix
  `pf-`). Callbacks sind reine Funktionen: nichts auf Disk, kein Modul-State, kein Logging von
  Eingaben.
- Daten aus dem Browser sind nicht vertrauenswürdig und laufen immer durch `browser_store`.
- Keine persönlichen Daten in Code, Tests, Doku oder Commits; das Repo ist öffentlich.

## Neues Eingabefeld: Checkliste

1. `storage/browser_store.py` → `SCENARIO_FIELDS`: Feld anhängen. Die Reihenfolge muss
   **exakt** der von `dashboard/callbacks.py` → `SCENARIO_INPUT_IDS` entsprechen, denn
   `values_to_inputs` arbeitet über die Position.
2. `FIELD_DEFAULTS`: Standardwert eintragen, sonst laden ältere Szenarien das Feld leer.
   Felder, deren leerer Wert etwas bedeutet (z. B. „leer = heute“), bekommen bewusst keinen.
3. `dashboard/layout.py`: Feld mit demselben Standardwert anlegen, am besten aus
   `FIELD_DEFAULTS` gelesen.
4. Testdaten nachziehen (Liste in `tests/CLAUDE.md`) und testen, dass ein Szenario aus einer
   älteren Version ohne das Feld noch lädt.
