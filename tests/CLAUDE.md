# Tests

- `unit/`: Rechenkern und Speicher, `ui/`: Callbacks und Layout (ohne Browser), `e2e/`:
  Playwright gegen einen echten Server (Marker `e2e`, in der CI Pflicht).
- **100 % Line- und Branch-Coverage** von `src/personal_finance` (`fail_under = 100`). Jeder
  neue Zweig braucht einen Test, auch Fehlermeldungen.
- Rechenbeispiele in Tests von Hand nachrechnen und im Kommentar zeigen (siehe
  `unit/test_home.py`).

## Callback-Tests

- `update_results(*browser_store.values_to_inputs({...}))` mit **vollständigen** Werten
  aufrufen. Ausgaben in der Reihenfolge `RESULT_SECTION_IDS`, danach der Hinweis.
- Diese Testdaten müssen jedes neue Feld kennen:
  - `VALID_INPUTS` in `ui/test_callbacks.py`
  - `_results(...)` in `ui/test_dashboard.py` (Übergabe über die Position!)
  - `sample_values` in `unit/test_browser_store.py`
  - `inputs` in `ui/test_user_isolation.py` (liest die Wohneigentum-Felder aus `FIELD_DEFAULTS`)
  - Die Felder von Haushalt und Person B kommen in den UI-Tests aus `FIELD_DEFAULTS` (eine
    Person). `sample_values` in `unit/test_browser_store.py` füllt beide Personen.
- Gespeicherte Szenarien sind verschachtelt (`values["household"]`, `values["persons"]["a"]`).
  e2e-Tests, die `localStorage` lesen, greifen so darauf zu.
- Person B hat dieselben Gruppentitel wie Person A (versteckt). In e2e-Tests Gruppen über
  `#person-a-inputs`, `#person-b-inputs` oder `#shared-groups` öffnen, sonst findet
  `get_by_text` zwei Treffer.
- Texte in DMC-Komponenten stecken nicht nur in `children`: `title` (Alert), `label` und
  `aria-label` sind eigene Props. Die Hilfsfunktion `texts()` in `ui/test_callbacks.py` sammelt
  alle.
- Testszenarien realistisch halten: Ein Vorbezug braucht ein PK-Guthaben, ein 3a-Plan am Limit
  lässt keinen Platz für verpfändete 3a-Zahlungen, eine zweite Ampel im Tab verschiebt Indizes.
  Ein „unerklärlicher“ Testfehler ist oft eine Regel, die richtig greift.
- Floats mit `pytest.approx` vergleichen, bei erwarteter 0 mit `abs=...`.

## e2e

- Fixtures in `e2e/conftest.py`: `alice`, `bob` (getrennte Browser-Kontexte = getrennte
  Nutzer), `phone_user` (390 × 844).
- Nach jeder Aktion `wait_until_idle()`: Dash markiert laufende Callbacks mit
  `[data-dash-is-loading="true"]`.
- Felder in eingeklappten Accordion-Gruppen sind unsichtbar und lassen sich nicht füllen.
  Zuerst die Gruppe öffnen.
