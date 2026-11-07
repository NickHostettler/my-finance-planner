"""The Dash application instance (assets are served from ``dashboard/assets``)."""

import dash

app = dash.Dash(__name__, title="Finanzplan | Schweizer Vorsorge")


@app.server.get("/health")
def health():
    """Liveness check for the hosting platform. Returns no user or system details."""
    return {"status": "ok"}, 200, {"Cache-Control": "no-store"}
