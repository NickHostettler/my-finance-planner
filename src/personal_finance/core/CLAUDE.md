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
  Jahren mit Erwerbseinkommen; eigene PK-Beiträge im Verhältnis zum Einkommen.
- `part_time.py` (#31): `pension_years` (versicherter Lohn, PK-Beitrag und 3a-Limit pro Jahr:
  klein mit PK, gross ohne PK), `ahv_monthly_pension` (Phasen senken den Durchschnitt,
  Erziehungsgutschriften ganz oder hälftig) und `compare_with_full_time` (Vorsorgelücke). Der
  fixe Koordinationsabzug muss exakt die BVG-Schätzung ohne Phasen ergeben (Test).
- Kinder werden im Kern als **Alter des Elternteils bei der Geburt** übergeben
  (`family.validate_birth_ages`). Gutschrift ab dem Jahr nach der Geburt bis zum Jahr, in dem
  das Kind 16 wird, eine pro Jahr.
- `family.py` (#32): Familienzulagen nach Alter des Kindes (bis 15 Kinder-, 16–24
  Ausbildungszulage, Beträge überschreibbar), EO im Geburtsjahr (80 %, Tageshöchstbetrag; Mutter
  98, anderer Elternteil 14 Taggelder, Zwillinge nicht doppelt) und was nach Kinderkosten und
  Sparen bleibt. Kinderkosten pro Phase in heutigen Franken, sie steigen mit der Inflation.
- Familien-Werte: Stand `FAMILY_RULES_AS_OF`; bei neuen Jahreswerten mitprüfen (Skill
  `jahreswerte`).

## Haushalt (v1.3)

- Jede Person rechnet wie ein Einzelplan; `household.py` enthält nur, was der Haushalt teilt:
  Zusammenleben (`MARRIED` gilt auch für eingetragene Partnerschaften), Aufteilung der
  Erziehungsgutschriften (verheiratet immer hälftig), AHV-Plafonierung 150 % (`couple_ahv`,
  in heutigen Franken) und Kinder aus Sicht von Person B (`shift_birth_ages`).
- `home_plan.plan_joint_purchase(inputs, members)`: ein Kauf mit einer oder zwei `Member`.
  Eigenmittel und Tragbarkeit mit den Summen, WEF-Limiten und Bezüge je Person
  (`HomePlan.members`, Pfade bis zur eigenen Pensionierung). Haushaltspfade und Amortisation
  enden bei der **ersten Pensionierung**. Verpfändete 3a nach freiem 3a-Platz aufgeteilt.
- Regression: `plan_purchase` (eine Person) ist `plan_joint_purchase` mit einem `Member` und
  muss exakt die Ergebnisse von v1.2 liefern. Einzelpläne prüfen Beträge mit den Meldungen
  aus `home.py`, Haushalte zusätzlich je Person mit „Person B: …“.
