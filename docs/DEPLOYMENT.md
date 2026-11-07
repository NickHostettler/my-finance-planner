# Deployment auf Render

Die App läuft als Docker-Container auf [Render](https://render.com) im Gratis-Plan.
Die Konfiguration steht als Blueprint in [`render.yaml`](../render.yaml) im Repository.

| | |
|---|---|
| URL | siehe Render-Dashboard → Dienst `my-finance-planner` (live seit 7.11.2026) |
| Plan | Free: 0.1 CPU, 512 MB RAM, 750 Instanz-Stunden/Monat |
| Region | Frankfurt (lässt sich nachträglich nicht ändern) |
| Deploy | automatisch bei Push auf `main`, **nur wenn die CI grün ist** (`autoDeployTrigger: checksPass`) |
| Health-Check | `GET /health` |
| Login | Benutzer `kamerad`, Passwort aus `APP_PASSWORD` |

**Einschränkungen des Gratis-Plans:** Nach 15 Minuten ohne Aufruf schläft die App ein; der
nächste Aufruf dauert dann etwa eine Minute. Dateien im Container gehen bei jedem Neustart
verloren. Das ist unproblematisch, weil die App nichts auf dem Server speichert.

## Einmalige Einrichtung

1. **Passwort erzeugen** (lokal, mindestens 12 Zeichen) und z.B. im Passwortmanager ablegen:
   ```bash
   uv run python -c "import secrets; print(secrets.token_urlsafe(18))"
   ```
2. Auf [dashboard.render.com](https://dashboard.render.com) mit **GitHub** anmelden.
3. **New → Blueprint** wählen.
4. Beim ersten Mal **„Connect GitHub“** und der Render-App Zugriff auf das Repository
   `my-finance-planner` geben (Zugriff auf ausgewählte Repositories reicht).
5. Das Repository auswählen. Render findet `render.yaml` und zeigt den Dienst
   `my-finance-planner` an.
6. Bei **`APP_PASSWORD`** das Passwort aus Schritt 1 eintragen.
7. **Apply / Deploy Blueprint** klicken. Der erste Build dauert einige Minuten.
8. Wenn der Dienst **Live** ist: die URL (`https://my-finance-planner….onrender.com`) öffnen
   und mit `kamerad` und dem Passwort anmelden.

## Kameraden einladen

Schicke **den Link und den Hinweis auf die [Kurzanleitung](ANLEITUNG.md)**. Das Passwort
sollte möglichst über einen **anderen Kanal** gehen als der Link (z.B. Link per Mail, Passwort
persönlich oder per Messenger), damit eine weitergeleitete Nachricht allein nicht reicht.

Beim ersten Öffnen zeigt die App jedem einen Hinweis: keine Beratung, Daten bleiben im eigenen
Browser, Bedeutung für Gerätewechsel und fremde Geräte. Mit „Verstanden“ wird er für diesen
Browser ausgeblendet. Über „Hinweise anzeigen“ in der Fusszeile lässt er sich wieder öffnen.
Wird der Text geändert, kann `NOTICE_VERSION` in `dashboard/callbacks.py` erhöht werden, damit
alle ihn erneut sehen.

**Passwort weitergegeben oder jemand soll keinen Zugang mehr haben?** Passwort ändern (siehe
unten) und den übrigen das neue mitteilen. Ihre gespeicherten Szenarien bleiben erhalten, weil
sie im jeweiligen Browser liegen.

## Betrieb

- **Neue Version:** PR nach `main` mergen. Render deployt automatisch, sobald alle CI-Checks
  grün sind. Ist ein Check rot, wird nicht deployt.
- **Passwort ändern:** Render → Dienst → *Environment* → `APP_PASSWORD` ändern → speichern.
  Render startet den Dienst neu. Den Kameraden das neue Passwort mitteilen.
  (Änderungen an `sync: false`-Variablen in `render.yaml` übernimmt Render nicht automatisch.)
- **Logs:** Render → Dienst → *Logs*. Sie enthalten keine Eingabewerte und keine IP-Adressen.
- **Fehlgeschlagener Deploy:** Render → Dienst → *Events*. Läuft die neue Version nicht, bleibt
  die vorherige online. Unter *Events* lässt sich auch auf eine frühere Version zurückrollen.
- **Kein Start ohne Passwort:** Fehlt `APP_PASSWORD`, verweigert der Container den Start
  (`refusing to start` im Log). So geht die App nie ungeschützt online.
