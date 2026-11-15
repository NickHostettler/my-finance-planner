---
name: pr
description: Bringt die aktuelle Arbeit als Pull Request gegen main auf GitHub (Branch prüfen, alle Checks lokal, Push, PR-Beschreibung auf Deutsch). Verwenden, wenn der Nutzer einen PR, einen Push zur Review oder „bring das auf GitHub“ verlangt.
---

# Pull Request

Push und PR sind öffentlich (das Repo ist öffentlich). Nur ausführen, wenn der Nutzer es
verlangt hat.

1. **Branch:** Nie auf `main` arbeiten. Steht die Arbeit auf `main`, zuerst einen Branch
   anlegen (`feature/<issue>-<kurzname>`, `fix/<kurzname>`, `chore/<kurzname>`).
2. **Arbeitsbaum sauber?** `git status`. Offene Änderungen in kleinen, thematisch getrennten
   Commits ablegen (Commit-Text auf Englisch, mit Issue-Nummer `(#27)`, falls vorhanden).
   Nichts committen, was persönliche Daten enthält; `.env` bleibt lokal.
3. **Checks lokal, alle müssen grün sein** (dieselben wie in der CI):
   ```powershell
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest -q --cov --ignore=tests/e2e
   uv run pytest tests/e2e
   ```
   Bei Änderungen an Layout, CSS, Karten, Grafiken oder Tabs zusätzlich den Skill `ui-check`.
4. **Push:** `git push -u origin <branch>`.
5. **PR gegen `main`** mit der GitHub CLI (evtl. nicht im PATH):
   ```powershell
   & "C:\Program Files\GitHub CLI\gh.exe" pr create --base main --title "<Titel>" --body-file <datei>
   ```
   Die Beschreibung in eine Datei im Scratchpad schreiben, nicht ins Repo. Aufbau, auf Deutsch:
   - **Zusammenfassung:** was sich für die Nutzerin oder den Nutzer ändert, dann die
     wichtigsten technischen Punkte. `Closes #<nr>` für erledigte Issues.
   - **Tests:** welche Checks liefen und mit welchem Ergebnis; was von Hand geprüft wurde.
   - **Manuell zu prüfen:** z. B. Gesetzestexte auf Fedlex, die sich nicht automatisch lesen
     lassen, oder Annahmen, die der Nutzer bestätigen soll. Weglassen, wenn es nichts gibt.
6. **Danach:** den Link zum PR nennen und die CI beobachten
   (`gh pr checks <nr> --watch`). Schlägt sie fehl, die Ursache beheben und nachschieben.
   Mergen tut der Nutzer; Render deployt nach grüner CI auf `main` von selbst.
