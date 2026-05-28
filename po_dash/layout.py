"""Top-level layout: an Inference tab and a Learning tab."""

from __future__ import annotations

from dash import dcc, html

from invoice_processing.tools.tools import list_inference_cases

CONTENT_STYLE = {"maxWidth": "1100px", "margin": "0 auto", "padding": "16px"}


def _inference_tab() -> html.Div:
    return html.Div(
        [
            html.H3("Run the processing pipeline"),
            html.P(
                "Select an existing case or upload a new document, then run the "
                "Acting → Investigation → ALF pipeline."
            ),
            html.Div(
                [
                    html.Label("Case"),
                    dcc.Dropdown(
                        id="inference-case-dropdown",
                        options=[{"label": c, "value": c} for c in list_inference_cases()],
                        placeholder="Select a case…",
                        style={"width": "320px"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),
            dcc.Upload(
                id="inference-upload",
                children=html.Div(
                    ["Drag and drop or ", html.A("select a PDF"), " to create a new case"]
                ),
                multiple=True,
                style={
                    "width": "100%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "6px",
                    "textAlign": "center",
                    "marginBottom": "12px",
                },
            ),
            html.Div(id="inference-upload-status", style={"marginBottom": "12px"}),
            dcc.Checklist(
                id="inference-skip-investigation",
                options=[{"label": " Skip investigation stage (faster)", "value": "skip"}],
                value=[],
                style={"marginBottom": "12px"},
            ),
            html.Button(
                "Run pipeline",
                id="inference-run-button",
                n_clicks=0,
                style={
                    "backgroundColor": "#0969da",
                    "color": "#fff",
                    "border": "none",
                    "padding": "8px 18px",
                    "borderRadius": "6px",
                    "cursor": "pointer",
                },
            ),
            dcc.Loading(
                id="inference-loading",
                type="default",
                children=html.Div(id="inference-results", style={"marginTop": "16px"}),
            ),
            dcc.Store(id="inference-store"),
        ],
        style={"padding": "16px 0"},
    )


def _learning_tab() -> html.Div:
    return html.Div(
        [
            html.H3("Learning: rule discovery & management"),
            html.Div(
                [
                    html.Label("Processed case"),
                    dcc.Dropdown(
                        id="learning-case-dropdown",
                        placeholder="Select a processed case…",
                        style={"width": "320px"},
                    ),
                    html.Button(
                        "Load case",
                        id="learning-load-button",
                        n_clicks=0,
                        style={"marginLeft": "8px"},
                    ),
                ],
                style={"display": "flex", "alignItems": "flex-end", "gap": "8px"},
            ),
            html.Div(id="learning-case-summary", style={"marginTop": "12px"}),
            html.Hr(),
            html.H4("Discover a rule from SME feedback"),
            dcc.Textarea(
                id="learning-feedback",
                placeholder="Describe what should have happened for this case…",
                style={"width": "100%", "height": "100px"},
            ),
            html.Button(
                "Discover rule",
                id="learning-discover-button",
                n_clicks=0,
                style={"marginTop": "8px"},
            ),
            dcc.Loading(
                type="default",
                children=html.Div(id="learning-discovery-output", style={"marginTop": "12px"}),
            ),
            html.Div(
                [
                    html.Button("Write rule to rule base", id="learning-write-button", n_clicks=0),
                ],
                style={"marginTop": "8px"},
            ),
            html.Div(id="learning-write-status", style={"marginTop": "8px"}),
            html.Hr(),
            html.H4("Existing rules"),
            html.Button("Refresh rules", id="learning-refresh-rules", n_clicks=0),
            html.Div(id="learning-rules-table", style={"marginTop": "8px"}),
            html.Div(
                [
                    html.Button(
                        "Delete selected rule",
                        id="learning-delete-button",
                        n_clicks=0,
                        style={"backgroundColor": "#cf222e", "color": "#fff", "border": "none",
                               "padding": "6px 14px", "borderRadius": "6px"},
                    ),
                ],
                style={"marginTop": "8px"},
            ),
            html.Div(id="learning-delete-status", style={"marginTop": "8px"}),
            dcc.Store(id="learning-proposed-rule"),
        ],
        style={"padding": "16px 0"},
    )


def serve_layout() -> html.Div:
    return html.Div(
        [
            html.H2("Document Processing Agent"),
            dcc.Tabs(
                id="main-tabs",
                value="inference",
                children=[
                    dcc.Tab(label="Inference", value="inference", children=_inference_tab()),
                    dcc.Tab(label="Learning", value="learning", children=_learning_tab()),
                ],
            ),
        ],
        style=CONTENT_STYLE,
    )
