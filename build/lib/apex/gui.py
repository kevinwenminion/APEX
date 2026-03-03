import os
import shlex
import subprocess
import sys
import webbrowser
from datetime import datetime
from threading import Timer
from typing import Any, Dict, List

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8060
BLOCKED_INLINE_COMMANDS = {"gui", "report"}


def _split_multi_values(raw_text: str) -> List[str]:
    if not raw_text:
        return []
    return [token.strip() for token in raw_text.replace(",", " ").split() if token.strip()]


def _build_feedback(message: str, ok: bool = False) -> Dict[str, Any]:
    return {
        "ok": ok,
        "message": message,
        "command": "",
        "returncode": "",
        "stdout": "",
        "stderr": "",
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def _run_apex_command(arguments: List[str]) -> Dict[str, Any]:
    command = [sys.executable, "-m", "apex", *arguments]
    try:
        completed = subprocess.run(
            command,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Failed to launch command: {exc}",
            "command": " ".join(shlex.quote(token) for token in command),
            "returncode": "",
            "stdout": "",
            "stderr": str(exc),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }

    return {
        "ok": completed.returncode == 0,
        "message": "Command finished successfully." if completed.returncode == 0 else "Command finished with errors.",
        "command": " ".join(shlex.quote(token) for token in command),
        "returncode": str(completed.returncode),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def _format_feedback(payload: Dict[str, Any]) -> str:
    if not payload:
        return "Click any action button to run an APEX command."

    lines = [f"[{payload.get('finished_at', '')}] {'SUCCESS' if payload.get('ok') else 'FAILED'}"]

    message = payload.get("message")
    if message:
        lines.append(message)
    command = payload.get("command")
    if command:
        lines.extend(["", f"$ {command}"])
    returncode = payload.get("returncode")
    if returncode != "":
        lines.append(f"Return code: {returncode}")

    stdout = payload.get("stdout")
    stderr = payload.get("stderr")
    if stdout:
        lines.extend(["", "[stdout]", stdout])
    if stderr:
        lines.extend(["", "[stderr]", stderr])
    if not stdout and not stderr:
        lines.extend(["", "(No command output)"])

    return "\n".join(lines)


def _resolve_triggered_id():
    if hasattr(dash, "ctx") and dash.ctx.triggered_id is not None:
        return dash.ctx.triggered_id
    triggered = dash.callback_context.triggered
    if not triggered:
        return None
    return triggered[0]["prop_id"].split(".")[0]


class ApexGuiApp:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, open_browser: bool = True):
        self.host = host
        self.port = port
        self.open_browser = open_browser
        dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.MATERIA, dbc_css],
            suppress_callback_exceptions=True,
        )
        self.app.title = "APEX GUI"
        self.app.layout = self._build_layout()
        self._register_callbacks()

    @staticmethod
    def _build_submit_tab() -> dbc.Tab:
        return dbc.Tab(
            label="Submit",
            children=[
                html.P("Use this form for `apex submit`.", className="text-muted"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Parameter JSON files (comma or space separated)"),
                                dbc.Input(id="submit-parameter", placeholder="param_joint.json"),
                            ],
                            md=8,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Global config"),
                                dbc.Input(id="submit-config", value="./global.json"),
                            ],
                            md=4,
                        ),
                    ],
                    className="g-2",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Work directories (optional)"),
                                dbc.Input(id="submit-work", value="."),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Flow type"),
                                dcc.Dropdown(
                                    id="submit-flow",
                                    clearable=False,
                                    value="auto",
                                    options=[
                                        {"label": "Auto detect", "value": "auto"},
                                        {"label": "relax", "value": "relax"},
                                        {"label": "props", "value": "props"},
                                        {"label": "joint", "value": "joint"},
                                    ],
                                ),
                            ],
                            md=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Workflow name (optional)"),
                                dbc.Input(id="submit-name", placeholder="my-apex-flow"),
                            ],
                            md=3,
                        ),
                    ],
                    className="g-2 mt-1",
                ),
                html.Br(),
                dbc.Label("Flags"),
                dcc.Checklist(
                    id="submit-flags",
                    options=[
                        {"label": "Debug mode (-d)", "value": "debug"},
                        {"label": "Submit only (-s)", "value": "submit_only"},
                    ],
                    value=[],
                    inputStyle={"marginRight": "6px", "marginLeft": "10px"},
                    labelStyle={"display": "inline-block", "marginRight": "14px"},
                ),
                html.Br(),
                dbc.Button("Run submit", id="submit-run", color="primary"),
            ],
        )

    @staticmethod
    def _build_manage_tab() -> dbc.Tab:
        return dbc.Tab(
            label="Manage",
            children=[
                html.P("Run common workflow management commands.", className="text-muted"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Command"),
                                dcc.Dropdown(
                                    id="manage-command",
                                    clearable=False,
                                    value="list",
                                    options=[
                                        {"label": "list", "value": "list"},
                                        {"label": "get", "value": "get"},
                                        {"label": "getsteps", "value": "getsteps"},
                                        {"label": "getkeys", "value": "getkeys"},
                                        {"label": "retrieve", "value": "retrieve"},
                                        {"label": "resubmit", "value": "resubmit"},
                                        {"label": "retry", "value": "retry"},
                                        {"label": "resume", "value": "resume"},
                                        {"label": "stop", "value": "stop"},
                                        {"label": "suspend", "value": "suspend"},
                                        {"label": "terminate", "value": "terminate"},
                                        {"label": "delete", "value": "delete"},
                                    ],
                                ),
                            ],
                            md=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Workflow ID"),
                                dbc.Input(id="manage-workflow-id", placeholder="Required for most commands"),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Config"),
                                dbc.Input(id="manage-config", value="./global.json"),
                            ],
                            md=5,
                        ),
                    ],
                    className="g-2",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Work directory"),
                                dbc.Input(id="manage-work", value="."),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Label for `list`"),
                                dbc.Input(id="manage-label", placeholder="key=value,key2=value2"),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Step ID (`retry -s` / `getsteps -i`)"),
                                dbc.Input(id="manage-step-id"),
                            ],
                            md=4,
                        ),
                    ],
                    className="g-2 mt-1",
                ),
                dbc.Row(
                    [
                        dbc.Col([dbc.Label("getsteps name"), dbc.Input(id="manage-name-filter")], md=3),
                        dbc.Col([dbc.Label("getsteps key"), dbc.Input(id="manage-key-filter")], md=3),
                        dbc.Col([dbc.Label("getsteps phase"), dbc.Input(id="manage-phase-filter")], md=3),
                        dbc.Col([dbc.Label("getsteps type"), dbc.Input(id="manage-type-filter")], md=3),
                    ],
                    className="g-2 mt-1",
                ),
                html.Br(),
                dbc.Button("Run command", id="manage-run", color="primary"),
            ],
        )

    @staticmethod
    def _build_advanced_tab() -> dbc.Tab:
        return dbc.Tab(
            label="Advanced",
            children=[
                html.P(
                    "Run any APEX command tail. Example: submit param_joint.json -c global_bohrium.json",
                    className="text-muted",
                ),
                dbc.Textarea(
                    id="advanced-command",
                    placeholder="submit param_joint.json -c global.json",
                    style={"height": "120px"},
                ),
                html.Br(),
                dbc.Button("Run advanced command", id="advanced-run", color="warning"),
                html.Div(
                    "Safety note: `report` and `gui` are blocked here to avoid nested Dash servers.",
                    className="text-muted mt-2",
                ),
            ],
        )

    def _build_layout(self) -> dbc.Container:
        return dbc.Container(
            [
                html.H2("APEX Graphical Interface", className="mt-3"),
                html.P(
                    "This dashboard wraps common `apex` CLI operations. Command output is shown below.",
                    className="text-muted",
                ),
                dcc.Store(id="command-result"),
                dbc.Tabs(
                    [
                        self._build_submit_tab(),
                        self._build_manage_tab(),
                        self._build_advanced_tab(),
                    ],
                    className="mb-3",
                ),
                html.Hr(),
                html.H4("Command Output"),
                html.Pre(
                    id="command-output",
                    style={
                        "whiteSpace": "pre-wrap",
                        "backgroundColor": "#111",
                        "color": "#f5f5f5",
                        "padding": "14px",
                        "borderRadius": "6px",
                        "maxHeight": "480px",
                        "overflowY": "auto",
                    },
                    children="Click any action button to run an APEX command.",
                ),
            ],
            fluid=True,
        )

    def _register_callbacks(self) -> None:
        @self.app.callback(
            Output("command-result", "data"),
            Input("submit-run", "n_clicks"),
            Input("manage-run", "n_clicks"),
            Input("advanced-run", "n_clicks"),
            State("submit-parameter", "value"),
            State("submit-config", "value"),
            State("submit-work", "value"),
            State("submit-flow", "value"),
            State("submit-name", "value"),
            State("submit-flags", "value"),
            State("manage-command", "value"),
            State("manage-workflow-id", "value"),
            State("manage-config", "value"),
            State("manage-work", "value"),
            State("manage-label", "value"),
            State("manage-step-id", "value"),
            State("manage-name-filter", "value"),
            State("manage-key-filter", "value"),
            State("manage-phase-filter", "value"),
            State("manage-type-filter", "value"),
            State("advanced-command", "value"),
            prevent_initial_call=True,
        )
        def _handle_command(
            _submit_clicks,
            _manage_clicks,
            _advanced_clicks,
            submit_parameter,
            submit_config,
            submit_work,
            submit_flow,
            submit_name,
            submit_flags,
            manage_command,
            manage_workflow_id,
            manage_config,
            manage_work,
            manage_label,
            manage_step_id,
            manage_name_filter,
            manage_key_filter,
            manage_phase_filter,
            manage_type_filter,
            advanced_command,
        ):
            triggered_id = _resolve_triggered_id()
            submit_flags = submit_flags or []

            if triggered_id == "submit-run":
                parameter_list = _split_multi_values(submit_parameter)
                if not parameter_list:
                    return _build_feedback("Please provide at least one parameter JSON file.")

                args = ["submit", *parameter_list]
                if submit_config:
                    args.extend(["-c", submit_config])
                work_list = _split_multi_values(submit_work)
                if work_list:
                    args.extend(["-w", *work_list])
                if submit_flow and submit_flow != "auto":
                    args.extend(["-f", submit_flow])
                if submit_name:
                    args.extend(["-n", submit_name])
                if "debug" in submit_flags:
                    args.append("-d")
                if "submit_only" in submit_flags:
                    args.append("-s")
                return _run_apex_command(args)

            if triggered_id == "manage-run":
                if not manage_command:
                    return _build_feedback("Please choose a management command.")
                args = [manage_command]
                if manage_command == "list":
                    if manage_label:
                        args.extend(["-l", manage_label])
                    if manage_config:
                        args.extend(["-c", manage_config])
                    return _run_apex_command(args)

                if manage_command == "getsteps":
                    if not manage_workflow_id:
                        return _build_feedback("`getsteps` requires a workflow ID.")
                    args.append(manage_workflow_id)
                    if manage_name_filter:
                        args.extend(["-n", manage_name_filter])
                    if manage_key_filter:
                        args.extend(["-k", manage_key_filter])
                    if manage_phase_filter:
                        args.extend(["-p", manage_phase_filter])
                    if manage_step_id:
                        args.extend(["-i", manage_step_id])
                    if manage_type_filter:
                        args.extend(["-t", manage_type_filter])
                else:
                    if manage_workflow_id:
                        args.extend(["-i", manage_workflow_id])
                    if manage_command == "retry" and manage_step_id:
                        args.extend(["-s", manage_step_id])

                if manage_work:
                    args.extend(["-w", manage_work])
                if manage_config:
                    args.extend(["-c", manage_config])
                return _run_apex_command(args)

            if triggered_id == "advanced-run":
                if not advanced_command or not advanced_command.strip():
                    return _build_feedback("Please provide a command tail.")
                try:
                    advanced_args = shlex.split(advanced_command.strip())
                except ValueError as exc:
                    return _build_feedback(f"Command parse error: {exc}")
                if advanced_args and advanced_args[0] == "apex":
                    advanced_args = advanced_args[1:]
                if not advanced_args:
                    return _build_feedback("Please provide arguments after `apex`.")
                if advanced_args[0] in BLOCKED_INLINE_COMMANDS:
                    return _build_feedback(
                        f"`apex {advanced_args[0]}` is blocked in Advanced mode to avoid nested Dash apps."
                    )
                return _run_apex_command(advanced_args)

            return _build_feedback("No action detected.")

        @self.app.callback(Output("command-output", "children"), Input("command-result", "data"))
        def _render_output(payload):
            return _format_feedback(payload)

    def run(self) -> None:
        host_for_browser = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        url = f"http://{host_for_browser}:{self.port}/"
        if self.open_browser:
            Timer(1.0, lambda: webbrowser.open(url)).start()
        print(f"APEX GUI server running at {url}")
        self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)


def gui_from_args(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    print("-------APEX GUI Mode-------")
    ApexGuiApp(host=host, port=port, open_browser=open_browser).run()
