---
name: jahreswerte
description: Aktualisiert die fachlichen Konstanten des Finanzplaners auf ein neues Jahr oder eine Gesetzesänderung (AHV/IV/EO, ALV, BVG-Grenzbeträge, 3a-Maximum, Wohneigentum, WEF) inklusive Quellen, Tests, Tab „Annahmen“ und Doku. Verwenden, wenn der Nutzer Sätze oder Grenzbeträge aktualisieren will oder nach „Werte 2027“, „neue Sätze“, „Stand prüfen“ fragt.
---

# Jahreswerte aktualisieren

Alle fachlichen Zahlen stehen in `src/personal_finance/config.py`, jeweils mit Quelle und
Stand im Kommentar. Kein Wert darf ohne Quelle geändert werden, und keine Quelle darf als
geprüft gelten, die nicht wirklich gelesen wurde.

1. **Bestand aufnehmen:** `config.py` durchgehen und pro Block notieren: Wert, Quelle, Stand.
   Werte ohne Quelle oder mit altem Stand (z. B. BVG-Grenzbeträge, 3a-Maximum) zuerst.
2. **Quellen lesen** (offizielle Stellen, keine Vergleichsportale):
   - AHV/IV/EO, ALV, AHV-Renten: Merkblätter der Informationsstelle AHV/IV (ahv-iv.ch),
     z. B. 2.01 Lohnbeiträge, 2.08 ALV, 3.01 Altersrenten.
   - BVG-Grenzbeträge (Eintrittsschwelle, Koordinationsabzug) und 3a-Maximum: BSV.
   - Wohneigentum: SBVg-Richtlinien; WEF: BVG/WEFV und BVV 3.
   - Fedlex lässt sich ohne JavaScript nicht automatisch lesen. Solche Stellen nicht als
     geprüft ausgeben, sondern im PR unter „Manuell zu prüfen“ auflisten.
3. **Dem Nutzer eine Tabelle zeigen** (alt → neu, Quelle, gültig ab) und bestätigen lassen,
   bevor etwas geändert wird. Reine Modellannahmen (Rendite, Inflation, Krankenkasse) nur
   auf ausdrücklichen Wunsch ändern; sie bleiben als „MODELLANNAHME“ gekennzeichnet.
4. **Ändern** in `config.py`: Wert, Quelle und Stand im Kommentar gemeinsam anpassen.
5. **Tests nachziehen:** Rechenbeispiele in `tests/unit` (Lohnabzüge, BVG, 3a, Wohneigentum,
   WEF) von Hand neu rechnen und die Rechnung im Kommentar zeigen. Ein Test, der nach der
   Änderung noch grün ist, obwohl er den Wert betrifft, prüft den Wert nicht: ergänzen.
6. **Texte nachziehen**, überall wo die Zahl oder das Jahr steht:
   - Tab „Annahmen“ und Hinweise in `dashboard/results.py` und `dashboard/home_view.py`
     (die meisten lesen aus `config`, feste Jahreszahlen und Quellen-Links nicht).
   - `docs/ANLEITUNG.md` und `README.md` (dort stehen einzelne Werte und „2026 rates“).
   - Mit Grep nach dem alten Wert in beiden Schreibweisen suchen (`7258`, `7’258`, `7'258`).
7. **Prüfen und abgeben:** `ruff check`, `ruff format --check`, Tests mit Coverage, Skill
   `ui-check` (Tab „Annahmen“ ansehen), dann Skill `pr`. Ändern sich Ergebnisse für
   bestehende Nutzer spürbar, ist das ein Release wert (Skill `release`).
