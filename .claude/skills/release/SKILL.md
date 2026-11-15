---
name: release
description: Veröffentlicht eine neue Version des Finanzplaners (Version in pyproject.toml, uv.lock, Tag, GitHub-Release, Deploy auf Render und Kurztest live). Verwenden, wenn ein Meilenstein fertig ist oder der Nutzer ein Release verlangt.
---

# Release

Vor dem Start mit dem Nutzer klären: Versionsnummer (SemVer: neue Funktionen = Minor) und
welche Issues bzw. welcher Meilenstein enthalten sind. Tag, GitHub-Release und Deploy sind
öffentlich und schwer rückgängig zu machen: **vor jedem dieser Schritte nachfragen.**

1. **Vorbereiten auf einem Branch** `release/<version>`:
   - `version` in `pyproject.toml` setzen, dann `uv lock` (aktualisiert `uv.lock`).
     `personal_finance.__version__` liest die Version aus den Paket-Metadaten, sonst ist nichts
     anzupassen. `tests/unit/test_version.py` prüft, dass alles übereinstimmt.
   - Doku aktuell? `docs/ANLEITUNG.md`, README (englischer Kopf, Highlights, Screenshot
     `docs/images/dashboard.png`), Tab „Annahmen“ mit Quellen und Stand.
   - `uv run ruff check .` und `uv run pytest -q --cov` grün, Skill `ui-check` ohne Probleme.
   - Commit „Release <version>“, Push, PR gegen `main` (Beschreibung auf Deutsch).
2. **Nach dem Merge** (macht der Nutzer oder mit seiner Zustimmung):
   - CI auf `main` abwarten. Render deployt erst, wenn die CI grün ist.
   - Tag und Release:
     ```powershell
     git switch main; git pull
     git tag -a v<version> -m "v<version> – <Titel>"
     git push origin v<version>
     & "C:\Program Files\GitHub CLI\gh.exe" release create v<version> --title "v<version> – <Titel>" --notes-file <datei>
     ```
   - Release-Notes auf Deutsch wie bei v1.0.0: kurzer Einleitungssatz, dann „## Highlights“
     mit Gruppen (🔒 Datenschutz, 🧮 Fachlich, 🚀 Betrieb, 🧹 Codebasis) und Issue-Nummern,
     danach „## Dokumentation“.
3. **Live prüfen:** Render-Dashboard → Deploy ist „Live“, `/health` antwortet, Login geht, die
   neue Funktion einmal durchklicken. Die URL und das Passwort stehen nicht im Repo; beim
   Nutzer nachfragen.
4. Meilenstein auf GitHub schliessen, sobald alle Issues zu sind.
