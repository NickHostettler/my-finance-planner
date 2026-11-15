# Dashboard (`dashboard/`)

`layout.py` ist statisch (Eingaben links, Ergebnisse rechts in Tabs). `callbacks.py` liest alle
Eingaben (`SCENARIO_INPUT_IDS`) und füllt die Tabs (`RESULT_SECTION_IDS`). Inhalte der Tabs
kommen aus `results.py` (Übersicht, Vorsorge, Annahmen) und `home_view.py` (Wohneigentum).
Bausteine (Karten, Eingabefelder, `money()`) stehen in `components.py`, Farben in `theme.py`,
eigenes CSS nur in `assets/dashboard.css`.

## Dash/Mantine-Stolperfallen

- **Versteckte Inhalte:** Accordion und Tabs brauchen `keepMounted=True` und
  `keepMountedMode="display-none"`. Der Mantine-Standard (React `<Activity>`) verzögert Updates
  in versteckten Bereichen, dann bleibt Dash ewig im Zustand „loading“ (in der CI nur auf
  langsamen Maschinen sichtbar). Popover ohne `keepMounted` ist in Ordnung.
- **Kein Callback darf dieselbe Property lesen und schreiben**, sonst entsteht ein Zyklus und
  Dash hängt. Ein Test prüft das.
- Properties, die mehrere Callbacks setzen, brauchen `allow_duplicate=True` und
  `prevent_initial_call=True`.
- `SegmentedControl` kennt nur **Strings**. Zahlen beim Lesen und Schreiben umwandeln
  (`_from_components` / `_to_components` in `callbacks.py`).
- Ein geleertes `NumberInput` liefert `""`, nicht `None`; `_from_components` macht `None` daraus.
- Prozent-Eingaben erst im Callback durch 100 teilen. Standardwerte als Literal (`5.0`), nicht
  als `0.05 * 100` (ergibt `5.000000000000001`).
- Ein Fehler in einem optionalen Bereich (z. B. Wohneigentum) erscheint nur in dessen Tab; die
  übrigen Tabs rechnen ohne diesen Bereich weiter.
- **Felder per Callback vorbelegen** (z. B. `fill_home_maximum`, #40): Das Laden eines Szenarios
  oder der letzten Eingaben ändert dieselben Auslöser und würde die geladenen Werte
  überschreiben. Darum schreiben `manage_scenarios` und `restore_last_inputs` eine Sperre in den
  `memory`-Store `HOME_PREFILL_SKIP_STORE_ID`; das Vorbelegen überspringt genau diese Änderung.
  `memory`-Stores sind die einzige Ausnahme von „jeder Store lokal mit `pf-`“ (ein Test prüft
  beides).
- Felder ein- und ausblenden über `style={"display": ...}` per Callback (siehe
  `update_home_controls`), nicht durch Entfernen aus dem Layout: Jedes Feld aus
  `SCENARIO_INPUT_IDS` muss immer im Layout stehen.

## Layout und Breiten

- Eingaben links in `AppShellNavbar` (`NAVBAR_WIDTH = 350`). Unter `MOBILE_BREAKPOINT = 768` px
  liegen sie hinter dem Burger-Menü.
- **Referenz Handy: 390 px Breite, kein horizontales Scrollen**
  (`document.documentElement.scrollWidth <= window.innerWidth`), und zwar **in jedem Tab**. Der
  e2e-Test dazu prüft alle Tabs, aber nur ohne geplanten Kauf; deshalb nach UI-Änderungen den
  Skill `ui-check` laufen lassen (mit `--home`). Referenz Desktop: 1440 px.
- Spalten responsiv: `dmc.Grid` mit `span={"base": 12, "lg": …}`, `dmc.SimpleGrid` mit
  `cols={"base": 1, "xs"/"sm": …}`. Mehrspaltig erst ab einem Breakpoint, nie bei `base`.
- Tabellen in `dmc.TableScrollContainer(minWidth=…)` mit `minWidth` ≤ 360 legen, damit sie in
  der Karte scrollen statt die Seite zu verbreitern.
- Keine festen Breiten in px für Inhalte; Kennzahlen (`metric-value`) kürzen mit Ellipse.
- **Grid-Spalten immer mit `minmax(0, 1fr)`, nie die implizite `auto`-Spalte.** Plotly zeichnet
  Grafiken in einem Tab, der beim Rendern versteckt ist (Vorsorge, Wohneigentum), mit der
  Standardbreite von 700 px. Eine `auto`-Spalte wächst auf diese Breite, auf dem Handy wird die
  Seite ca. 750 px breit, und die Grafik schrumpft nie mehr. Deshalb hat `.results-column`
  `grid-template-columns: minmax(0, 1fr)`. `min-width: 0` auf einzelnen Karten oder Grafiken
  löst das **nicht**; die Ursache ist der äusserste Grid-Container. Allgemein: Wird die Seite zu
  breit, zuerst mit `ui-check` das äusserste zu breite Element suchen statt innen zu flicken.

## Texte

- Du-Form, kurze Sätze, Schweizer Schreibweise. Beträge mit `money()` formatieren.
- Fehlermeldungen sagen, was zu tun ist („Bitte gib … ein“), Begründungen nennen die Zahl
  („Es fehlen CHF 18’000 harte Eigenmittel“).
- Was das Modell nicht rechnet (Steuern, individuelle Bank- oder Kassenregeln), steht als
  Hinweis im UI und im Tab „Annahmen“. Kein Text darf wie eine Beratung klingen.
