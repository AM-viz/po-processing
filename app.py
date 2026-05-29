"""
Dash application entrypoint for the document-processing agent.

Runs locally (``python app.py``) and as a Databricks App. Storage is rooted at
``VOLUME_BASE`` (a Databricks Volume) when set, else the package-local ``data``
directory. Inference is served by AWS Bedrock (see
``po_processing/core/llm_client.py``).
"""

from __future__ import annotations

import os

import dash
from dash import Dash

from po_dash import callbacks_inference, callbacks_learning
from po_dash.layout import serve_layout


def _make_background_manager():
    """Return a Dash background-callback manager if diskcache is available."""
    try:
        import diskcache  # noqa: PLC0415

        cache_dir = os.getenv("DASH_CACHE_DIR", "/tmp/po_dash_cache")
        cache = diskcache.Cache(cache_dir)
        return dash.DiskcacheManager(cache)
    except Exception:
        return None


_manager = _make_background_manager()

app = Dash(
    __name__,
    title="Document Processing Agent",
    background_callback_manager=_manager,
    suppress_callback_exceptions=True,
)
# WSGI handle for gunicorn / Databricks Apps.
server = app.server
app.layout = serve_layout

callbacks_inference.register(app, background=_manager is not None)
callbacks_learning.register(app, background=_manager is not None)


def main() -> None:
    port = int(
        os.environ.get("DATABRICKS_APP_PORT", os.environ.get("PORT", "8050"))
    )
    app.run(host="0.0.0.0", port=port, debug=bool(os.getenv("DASH_DEBUG")))


if __name__ == "__main__":
    main()
