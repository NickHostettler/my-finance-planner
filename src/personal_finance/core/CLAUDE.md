# Rechenkern (`core/`)

- **Reine Funktionen** ohne Dash-Import, ohne I/O, ohne globalen Zustand. Ergebnisse als
  `@dataclass(frozen=True)`.
- **Eingaben selbst prüfen** und bei Fehlern `ValueError` mit einer **deutschen,
  verständlichen Meldung** werfen. Das Dashboard zeigt diese Meldung 1:1 an. Prüfen auf:
  `None`, `bool` (ist in Python ein `int`!), Text, `nan`/`inf`, negative Werte, Bereichsgrenzen.
- **Fachliche Regeln** gehören als Konstante mit Quelle (Gesetz/Artikel oder URL) und Stand nach
  `config.py`, nicht als Zahl in den Code. Reine Modellannahmen ausdrücklich als
  „MODELLANNAHME“ kennzeichnen.
- Fedlex-Seiten (Gesetzestexte) lassen sich ohne JavaScript nicht automatisch lesen. Solche
  Links und Zitate nicht als „geprüft“ ausgeben; im PR erwähnen, was manuell zu prüfen ist.
- Geldbeträge in Meldungen: `CHF 18’000` (Apostroph ’ als Tausendertrennzeichen).
- Prozentsätze im Kern immer als Dezimalzahl (`0.05`). Die Umrechnung aus Prozent-Eingaben
  passiert im Dashboard.

## Prognose

- `projection.project_balance`: Werte am Anfang jedes Jahres, Index 0 = heute. Einzahlungen zu
  Jahresbeginn, danach Rendite. `withdrawals={jahr: betrag}` zieht zu einem Zeitpunkt etwas ab
  (nie unter 0). Ohne `withdrawals` muss das Ergebnis exakt gleich bleiben wie vorher
  (Regressionstests).
- Nominal rechnen, die reale Sicht erst bei der Anzeige mit `deflate()` umrechnen.

## Wohneigentum (v1.1)

- `home.py`: Tragbarkeit, Eigenmittel, max. Kaufpreis (SBVg-Richtlinien, Bankpraxis).
- `wef.py`: Vorbezug 2. Säule / 3a (Mindestbetrag, Regel ab 50, Frist vor Pensionierung,
  5-Jahres-Regel).
- `mortgage.py`: direkte/indirekte Amortisation, Tragbarkeit im Alter.
- `home_plan.py`: verbindet die Eingaben mit den Regeln und der Prognose (mit/ohne Kauf).
  `available_funds` und `suggested_amounts` liefern die Höchstbeträge zum Kaufalter (#40):
  Reihenfolge 3b → 3a → Pensionskasse, gekürzt auf Kaufpreis plus Nebenkosten, kein PK-Bezug
  unter dem WEF-Mindestbetrag.
- Annahmen, die im UI erklärt werden müssen (Wohneigentum): Immobilie bleibt zum Kaufpreis (keine
  Wertveränderung); Wohnkosten werden aus dem laufenden Einkommen bezahlt; Erspartes über das
  prognostizierte freie Vermögen hinaus kommt „von ausserhalb“.

## Lebensphasen (v1.2)

- `life_phases.py`: `LifePhase` (Alter von–bis inklusive, Pensum als Dezimalzahl, Einkommen pro
  Monat auf derselben Basis wie die Einkommenseingabe), `validate_phases` (lückenlos, ohne
  Überschneidung, von heute bis zum Jahr vor der Pensionierung) und `yearly_plan` (ein Wert pro
  Jahr, Index 0 = heute). Die Listen gehen direkt in `project_balance`.
- Regression: `full_time_phase` (eine Phase, 100 %) muss exakt die Reihen ohne Phasen ergeben.
- Modellannahmen: Phaseneinkommen in heutigen Franken plus Lohnzunahme ab heute; 3a nur in
  Jahren mit Erwerbseinkommen; eigene PK-Beiträge im Verhältnis zum Einkommen. Die BVG-Regeln
  für Teilzeit (Eintrittsschwelle, Koordinationsabzug) folgen mit #31.
