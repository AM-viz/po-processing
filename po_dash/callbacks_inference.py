"""Inference-tab callbacks: upload, run pipeline, render results."""

from __future__ import annotations

import base64
import contextlib
import io
from datetime import datetime, timezone

from dash import Input, Output, State, html, no_update

from po_processing import run_inference
from po_processing.core import storage
from po_processing.tools.tools import list_inference_cases

from . import components


def _save_uploaded_files(contents: list[str], filenames: list[str]) -> str:
    """Persist uploaded PDFs into a new case folder; return the case id."""
    case_id = datetime.now(timezone.utc).strftime("uploaded_%Y%m%d_%H%M%S")
    case_dir = storage.EXEMPLARY_DIR / case_id
    for content, name in zip(contents, filenames, strict=False):
        _, b64 = content.split(",", 1)
        data = base64.b64decode(b64)
        safe_name = name if name.lower().endswith(".pdf") else f"{name}.pdf"
        storage.write_bytes(case_dir / safe_name, data)
    return case_id


def _render_results(result: dict, logs: str) -> html.Div:
    status = result.get("status", "UNKNOWN")
    children = [
        components.section_title(f"Pipeline status: {status}"),
        components.decision_badge("Acting decision", result.get("acting_decision")),
        components.decision_badge(
            "Investigation", result.get("investigation_compliance")
        ),
        html.Div(f"Investigation score: {result.get('investigation_score', 0)}"),
        html.Div(
            f"ALF revised: {result.get('alf_revised')} "
            f"(rules matched: {result.get('alf_rules_matched', 0)})"
        ),
        html.Div(f"Pipeline time: {result.get('pipeline_time', 0):.1f}s"),
    ]

    if result.get("error"):
        children.append(html.Div(f"Error: {result['error']}", style={"color": "#cf222e"}))

    children.append(html.Hr())
    children.append(components.section_title("Stages"))
    children.append(components.stages_table(result.get("stages")))

    # Final output JSON, read from the path the pipeline reported.
    final_path = result.get("final_output")
    if final_path and storage.exists(final_path):
        try:
            children.append(html.Hr())
            children.append(components.section_title("Final output"))
            children.append(components.json_viewer(storage.read_json(final_path)))
        except Exception:
            pass

    children.append(html.Hr())
    children.append(components.section_title("Run log"))
    children.append(components.log_panel(logs))
    return html.Div(children, style=components.CARD_STYLE)


def register(app, background: bool) -> None:
    @app.callback(
        Output("inference-upload-status", "children"),
        Output("inference-case-dropdown", "options"),
        Output("inference-case-dropdown", "value"),
        Input("inference-upload", "contents"),
        State("inference-upload", "filename"),
        prevent_initial_call=True,
    )
    def _on_upload(contents, filenames):
        if not contents:
            return no_update, no_update, no_update
        case_id = _save_uploaded_files(contents, filenames)
        options = [{"label": c, "value": c} for c in list_inference_cases()]
        return (
            html.Span(f"Created case '{case_id}'.", style={"color": "#1a7f37"}),
            options,
            case_id,
        )

    callback_kwargs = {
        "output": Output("inference-results", "children"),
        "inputs": Input("inference-run-button", "n_clicks"),
        "state": [
            State("inference-case-dropdown", "value"),
            State("inference-skip-investigation", "value"),
        ],
        "prevent_initial_call": True,
    }
    if background:
        callback_kwargs["background"] = True

    @app.callback(**callback_kwargs)
    def _on_run(n_clicks, case_id, skip_value):
        if not case_id:
            return html.Div(
                "Please select or upload a case first.", style={"color": "#cf222e"}
            )
        skip = "true" if skip_value and "skip" in skip_value else "false"
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                result = run_inference(case_id, skip)
        except Exception as exc:
            result = {"status": "ERROR", "error": str(exc)}
        return _render_results(result, buffer.getvalue())
