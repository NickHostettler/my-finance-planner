---
name: ui-check
description: Prüft alle Ergebnis-Tabs des Dashboards im echten Browser auf Handybreite (390 px) und Desktopbreite (1440 px), meldet horizontales Scrollen und JavaScript-Fehler und erstellt Screenshots. Verwenden nach jeder Änderung an Layout, CSS, Karten, Grafiken oder Tabs, bevor committet wird.
---

# UI-Check

1. Einmalig: `uv sync --group e2e` und `uv run playwright install chromium`.
2. Prüfung starten, die Screenshots in den Scratchpad-Ordner schreiben (nicht ins Repo):

   ```powershell
   uv run python scripts/ui_check.py <scratchpad>\ui-check --home
   ```

   `--home` plant vorher einen Wohnungskauf, damit der Tab „Wohneigentum“ alle Inhalte zeigt.
   Ohne `--home` wird der Zustand ohne Kauf geprüft. Bei Änderungen am Wohneigentum beides
   laufen lassen.
3. Ergebnis lesen: Jede Zeile nennt Breite, Tab und Seitenbreite. `ZU BREIT` nennt die
   äussersten Elemente, ab denen die Seite breiter wird als der Bildschirm. Exit-Code 1
   heisst: Problem gefunden.
4. Die Screenshots der geänderten Tabs mit dem Read-Tool ansehen (Handy und Desktop) und auf
   abgeschnittene Texte, Überlappungen, leere Karten und unlesbare Grafiken prüfen.
5. Probleme beheben, bevor committet wird. Regeln zu Breiten und Mantine-Stolperfallen stehen
   in `src/personal_finance/dashboard/CLAUDE.md`. Neue Erkenntnisse dort nachtragen.
