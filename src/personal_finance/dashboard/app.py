"""The Dash application instance (assets are served from ``dashboard/assets``)."""

import dash
from dash import _dash_renderer

# Dash Mantine Components 3 needs React 19. Dash 4.5 ships it but still loads React 18 by
# default, so it is selected here, before the app is created.
REACT_VERSION = "19.2.4"
_dash_renderer._set_react_version(REACT_VERSION)

app = dash.Dash(__name__, title="Finanzplan | Schweizer Vorsorge")


@app.server.get("/health")
def health():
    """Liveness check for the hosting platform. Returns no user or system details."""
    return {"status": "ok"}, 200, {"Cache-Control": "no-store"}
