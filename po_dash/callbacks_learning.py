"""Learning-tab callbacks: load case, discover/write/delete rules."""

from __future__ import annotations

import json

from dash import Input, Output, State, html, no_update

from po_processing.tools.tools import (
    delete_rule,
    discover_safe_rule,
    get_existing_rules,
    list_cases,
    load_case,
    write_rule,
)

from . import components


def register(app, background: bool) -> None:  # noqa: C901
    # background unused here; many small callbacks keep this function long.
    # Populate the processed-case dropdown when the Learning tab is shown.
    @app.callback(
        Output("learning-case-dropdown", "options"),
        Input("main-tabs", "value"),
    )
    def _populate_cases(tab):
        if tab != "learning":
            return no_update
        return [{"label": c, "value": c} for c in list_cases()]

    @app.callback(
        Output("learning-case-summary", "children"),
        Input("learning-load-button", "n_clicks"),
        State("learning-case-dropdown", "value"),
        prevent_initial_call=True,
    )
    def _load_case(n_clicks, case_id):
        if not case_id:
            return html.Em("Select a case first.")
        try:
            data = load_case(case_id)
        except Exception as exc:
            return html.Div(f"Failed to load case: {exc}", style={"color": "#cf222e"})
        return html.Div(
            [
                components.decision_badge("Decision", data.get("decision")),
                html.Div(f"Rejection reason: {data.get('rejection_reason') or '—'}"),
                html.Div(f"Rejection phase: {data.get('rejection_phase') or '—'}"),
                html.Details(
                    [html.Summary("Case summary"), html.Pre(data.get("summary", ""))]
                ),
            ],
            style=components.CARD_STYLE,
        )

    @app.callback(
        Output("learning-discovery-output", "children"),
        Output("learning-proposed-rule", "data"),
        Input("learning-discover-button", "n_clicks"),
        State("learning-case-dropdown", "value"),
        State("learning-feedback", "value"),
        prevent_initial_call=True,
    )
    def _discover(n_clicks, case_id, feedback):
        if not case_id or not feedback:
            return html.Em("Select a case and enter feedback."), no_update
        try:
            result = discover_safe_rule(case_id, feedback)
        except Exception as exc:
            return html.Div(f"Discovery failed: {exc}", style={"color": "#cf222e"}), no_update
        rule = result.get("rule") or result.get("proposed_rule") or result
        return (
            html.Div(
                [
                    components.section_title("Proposed rule"),
                    components.json_viewer(result),
                ],
                style=components.CARD_STYLE,
            ),
            rule,
        )

    @app.callback(
        Output("learning-write-status", "children"),
        Input("learning-write-button", "n_clicks"),
        State("learning-proposed-rule", "data"),
        prevent_initial_call=True,
    )
    def _write(n_clicks, rule):
        if not rule:
            return html.Em("Discover a rule first.")
        try:
            result = write_rule(json.dumps(rule), "add")
        except Exception as exc:
            return html.Div(f"Write failed: {exc}", style={"color": "#cf222e"})
        return html.Div(f"Wrote rule: {result}", style={"color": "#1a7f37"})

    @app.callback(
        Output("learning-rules-table", "children"),
        Input("learning-refresh-rules", "n_clicks"),
        Input("learning-write-button", "n_clicks"),
        Input("learning-delete-button", "n_clicks"),
        prevent_initial_call=False,
    )
    def _refresh_rules(*_clicks):
        try:
            rules = get_existing_rules()
        except Exception:
            rules = []
        return components.rules_table(rules)

    @app.callback(
        Output("learning-delete-status", "children"),
        Input("learning-delete-button", "n_clicks"),
        State("rules-data-table", "selected_rows"),
        State("rules-data-table", "data"),
        prevent_initial_call=True,
    )
    def _delete(n_clicks, selected_rows, table_data):
        if not selected_rows or not table_data:
            return html.Em("Select a rule row to delete.")
        rule_id = table_data[selected_rows[0]].get("id")
        try:
            result = delete_rule(rule_id)
        except Exception as exc:
            return html.Div(f"Delete failed: {exc}", style={"color": "#cf222e"})
        return html.Div(f"Deleted {rule_id}: {result}", style={"color": "#1a7f37"})
