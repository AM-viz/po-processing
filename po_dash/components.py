"""Reusable rendering helpers for the Dash UI."""

from __future__ import annotations

import json
from typing import Any

from dash import dash_table, dcc, html

# ---------------------------------------------------------------------------
# Styling primitives
# ---------------------------------------------------------------------------

CARD_STYLE = {
    "border": "1px solid #d0d7de",
    "borderRadius": "8px",
    "padding": "16px",
    "marginBottom": "16px",
    "backgroundColor": "#ffffff",
}

DECISION_COLORS = {
    "ACCEPT": "#1a7f37",
    "REJECT": "#cf222e",
    "ERROR": "#9a6700",
}


def section_title(text: str) -> html.H4:
    return html.H4(text, style={"marginTop": "0", "marginBottom": "8px"})


def decision_badge(label: str, value: str | None) -> html.Div:
    color = DECISION_COLORS.get((value or "").upper(), "#57606a")
    return html.Div(
        [
            html.Span(f"{label}: ", style={"fontWeight": "600"}),
            html.Span(
                value or "—",
                style={
                    "color": "#ffffff",
                    "backgroundColor": color,
                    "padding": "2px 10px",
                    "borderRadius": "12px",
                    "fontWeight": "600",
                },
            ),
        ],
        style={"marginBottom": "8px"},
    )


def json_viewer(obj: Any, max_height: str = "400px") -> dcc.Markdown:
    try:
        text = json.dumps(obj, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(obj)
    return dcc.Markdown(
        f"```json\n{text}\n```",
        style={
            "maxHeight": max_height,
            "overflow": "auto",
            "border": "1px solid #eaeef2",
            "borderRadius": "6px",
            "padding": "8px",
        },
    )


def log_panel(text: str) -> html.Pre:
    return html.Pre(
        text or "",
        style={
            "maxHeight": "300px",
            "overflow": "auto",
            "backgroundColor": "#0d1117",
            "color": "#c9d1d9",
            "padding": "12px",
            "borderRadius": "6px",
            "fontSize": "12px",
            "whiteSpace": "pre-wrap",
        },
    )


def stages_table(stages: dict | None) -> Any:
    """Render the per-stage result dict from run_inference as a table."""
    if not stages:
        return html.Em("No stage details.")
    rows = []
    for name, info in stages.items():
        if isinstance(info, dict):
            detail = ", ".join(f"{k}={v}" for k, v in info.items())
        else:
            detail = str(info)
        rows.append({"stage": name, "detail": detail})
    return dash_table.DataTable(
        data=rows,
        columns=[
            {"name": "Stage", "id": "stage"},
            {"name": "Detail", "id": "detail"},
        ],
        style_cell={
            "textAlign": "left",
            "fontFamily": "monospace",
            "fontSize": "12px",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_header={"fontWeight": "600", "backgroundColor": "#f6f8fa"},
        style_table={"overflowX": "auto"},
    )


def rules_table(rules: list[dict] | None) -> Any:
    if not rules:
        return html.Em("No rules in the rule base yet.")
    rows = []
    for r in rules:
        rows.append(
            {
                "id": r.get("id", ""),
                "name": r.get("name", ""),
                "scope": r.get("scope", ""),
                "priority": r.get("priority", ""),
            }
        )
    return dash_table.DataTable(
        id="rules-data-table",
        data=rows,
        columns=[
            {"name": "ID", "id": "id"},
            {"name": "Name", "id": "name"},
            {"name": "Scope", "id": "scope"},
            {"name": "Priority", "id": "priority"},
        ],
        row_selectable="single",
        style_cell={"textAlign": "left", "fontSize": "13px"},
        style_header={"fontWeight": "600", "backgroundColor": "#f6f8fa"},
        style_table={"overflowX": "auto"},
    )
