import copy
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from threading import Timer
from typing import Any, Dict, List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dash_table, dcc, html

from apex.account import DEFAULT_BOHRIUM_CONFIG, get_account_config_path, load_account_config, save_account_config


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8060
BLOCKED_INLINE_COMMANDS = {"gui", "report"}
DEFAULT_SUBMIT_COMMAND = "nohup apex submit param.json -c global.json > apex.log 2>&1 &"

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_DIR = os.path.join(THIS_DIR, "default_config")
PROFILE_NAMES = ("lammps", "vasp", "abacus")
DEFAULT_PROFILE = "lammps"

LMP_INTERACTION_TYPE_OPTIONS = ["eam_alloy", "deepmd", "meam", "tersoff", "sw", "reaxff"]


def _load_json_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_dump_text(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=4, ensure_ascii=False)


def _profile_dir(profile: str) -> str:
    profile_name = profile if profile in PROFILE_NAMES else DEFAULT_PROFILE
    return os.path.join(DEFAULT_CONFIG_DIR, profile_name)


def _load_profile_global(profile: str) -> Dict[str, Any]:
    return _load_json_file(os.path.join(_profile_dir(profile), "global.json"))


def _load_profile_param_template(profile: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for filename in (
        "param_structure.json",
        os.path.join("param_interaction", "param_interaction.json"),
        "param_relax.json",
        "param_props.json",
    ):
        part = _load_json_file(os.path.join(_profile_dir(profile), filename))
        if isinstance(part, dict):
            payload.update(copy.deepcopy(part))
    return payload


def _extract_property_types(param_template: Dict[str, Any]) -> List[str]:
    ordered: List[str] = []
    for item in param_template.get("properties", []):
        if not isinstance(item, dict):
            continue
        ptype = item.get("type")
        if ptype and ptype not in ordered:
            ordered.append(ptype)
    return ordered


def _extract_selected_properties(param_template: Dict[str, Any]) -> List[str]:
    selected: List[str] = []
    for item in param_template.get("properties", []):
        if not isinstance(item, dict):
            continue
        ptype = item.get("type")
        if ptype and item.get("req_calc") and ptype not in selected:
            selected.append(ptype)
    return selected


def _extract_interaction_defaults(param_template: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    interaction = param_template.get("interaction")
    if not isinstance(interaction, dict):
        return "eam_alloy", "", []
    interaction_type = interaction.get("type") or "eam_alloy"
    interaction_model_obj = interaction.get("model")
    if isinstance(interaction_model_obj, list):
        interaction_model = ", ".join(str(item) for item in interaction_model_obj)
    else:
        interaction_model = interaction_model_obj or ""
    type_map = interaction.get("type_map")
    if isinstance(type_map, dict):
        elements = list(type_map.keys())
    else:
        elements = []
    return interaction_type, interaction_model, elements


def _extract_interaction_incar(param_template: Dict[str, Any]) -> str:
    interaction = param_template.get("interaction")
    if not isinstance(interaction, dict):
        return ""
    return interaction.get("incar") or ""


def _extract_potcar_rows(param_template: Dict[str, Any]) -> List[Tuple[str, str]]:
    interaction = param_template.get("interaction")
    if not isinstance(interaction, dict):
        return []
    potcars = interaction.get("potcars")
    if not isinstance(potcars, dict):
        return []
    return [(str(ele), _strip_parenthetical_suffix(str(path))) for ele, path in potcars.items()]


def _extract_orb_rows(param_template: Dict[str, Any]) -> List[Tuple[str, str]]:
    interaction = param_template.get("interaction")
    if not isinstance(interaction, dict):
        return []
    orb_files = interaction.get("orb_files")
    if not isinstance(orb_files, dict):
        return []
    return [(str(ele), _strip_parenthetical_suffix(str(path))) for ele, path in orb_files.items()]


def _strip_parenthetical_suffix(text: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", (text or "").strip())


def _interaction_type_options_for_profile(profile: str, default_type: str) -> List[Dict[str, str]]:
    if profile == "lammps":
        options = list(LMP_INTERACTION_TYPE_OPTIONS)
        if default_type and default_type not in options:
            options.insert(0, default_type)
    elif profile in {"vasp", "abacus"}:
        options = [profile]
        if default_type and default_type not in options:
            options.insert(0, default_type)
    else:
        options = list(LMP_INTERACTION_TYPE_OPTIONS)
    return [{"label": item, "value": item} for item in options]


def _rows_to_mapping(keys: List[str], values: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for key, value in zip(keys, values):
        k = (key or "").strip()
        v = _strip_parenthetical_suffix(value or "")
        if k and v and k not in mapping:
            mapping[k] = v
    return mapping


def _interaction_table_columns_for_profile(profile: str) -> List[Dict[str, str]]:
    base = [
        {"id": "element", "name": "Element"},
        {"id": "potcar", "name": "POTCAR"},
    ]
    if profile == "abacus":
        base.append({"id": "orb_file", "name": "ORB file"})
    return base


def _interaction_table_rows_from_template(profile: str, param_template: Dict[str, Any]) -> List[Dict[str, str]]:
    potcar_map = dict(_extract_potcar_rows(param_template))
    orb_map = dict(_extract_orb_rows(param_template))
    ordered_elements = list(potcar_map.keys())
    for ele in orb_map.keys():
        if ele not in ordered_elements:
            ordered_elements.append(ele)

    rows: List[Dict[str, str]] = []
    for ele in ordered_elements:
        row = {
            "element": ele,
            "potcar": potcar_map.get(ele, ""),
        }
        if profile == "abacus":
            row["orb_file"] = orb_map.get(ele, "")
        rows.append(row)

    if not rows:
        rows.append({"element": "", "potcar": "", **({"orb_file": ""} if profile == "abacus" else {})})
    return rows


def _interaction_editor_label(profile: str) -> str:
    if profile == "vasp":
        return "INCAR 编辑区"
    if profile == "abacus":
        return "INPUT 编辑区"
    return "INCAR/INPUT 编辑区"


def _load_profile_incar_content(profile: str, param_template: Dict[str, Any]) -> str:
    incar_rel = _strip_parenthetical_suffix(_extract_interaction_incar(param_template))
    if not incar_rel:
        return ""
    source_path = os.path.join(_profile_dir(profile), "param_interaction", incar_rel)
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


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


def _resolve_triggered_id():
    if hasattr(dash, "ctx") and dash.ctx.triggered_id is not None:
        return dash.ctx.triggered_id
    triggered = dash.callback_context.triggered
    if not triggered:
        return None
    return triggered[0]["prop_id"].split(".")[0]


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


def _read_log_tail(log_path: str = "apex.log", max_lines: int = 400) -> str:
    if not os.path.isfile(log_path):
        return f"{log_path} not found yet. Run submit first."
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as exc:
        return f"Failed to read {log_path}: {exc}"
    return "".join(lines[-max_lines:]) if lines else f"{log_path} is empty."


def _parse_extra_elements(raw_text: str) -> List[str]:
    if not raw_text:
        return []
    normalized = raw_text.replace(",", " ").replace(";", " ").replace("\n", " ")
    return [token.strip() for token in normalized.split() if token.strip()]


def _merge_dict_values(base: Dict[str, Any], updates: Optional[Dict[str, Any]]) -> None:
    if not updates:
        return
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_dict_values(base[key], value)
        else:
            base[key] = value


def _load_account_state(account_path: Optional[str] = None) -> Dict[str, Any]:
    path_obj = get_account_config_path(account_path)
    raw_config = load_account_config(path_obj)
    merged = copy.deepcopy(DEFAULT_BOHRIUM_CONFIG)
    if isinstance(raw_config, dict):
        _merge_dict_values(merged, raw_config)
    program_id = merged.get("program_id")
    return {
        "path": str(path_obj),
        "email": str(merged.get("email") or ""),
        "program_id": str(program_id) if program_id not in (None, "") else "",
        "password_set": bool(merged.get("password")),
    }


def _render_account_summary(account_state: Dict[str, Any]) -> str:
    email = account_state.get("email") or "(未设置)"
    program_id = account_state.get("program_id") or "(未设置)"
    password_status = "已设置 (隐藏)" if account_state.get("password_set") else "未设置"
    config_path = account_state.get("path") or "(unknown)"
    return "\n".join(
        [
            f"Config path: {config_path}",
            f"Email: {email}",
            f"Program ID: {program_id}",
            f"Password: {password_status}",
        ]
    )


def _brief_feedback(payload: Dict[str, Any]) -> str:
    if not payload:
        return ""
    status = "SUCCESS" if payload.get("ok") else "FAILED"
    message = payload.get("message") or ""
    ts = payload.get("finished_at") or datetime.now().isoformat(timespec="seconds")
    return f"[{ts}] {status} {message}"


def _save_account_overwrite(
    email: str,
    password: str,
    program_id_text: str,
    account_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    path_obj = get_account_config_path(account_path)
    raw_config = load_account_config(path_obj)
    merged = copy.deepcopy(DEFAULT_BOHRIUM_CONFIG)
    if isinstance(raw_config, dict):
        _merge_dict_values(merged, raw_config)

    updates_applied: List[str] = []
    clean_email = (email or "").strip()
    clean_password = (password or "").strip()
    clean_program_id = (program_id_text or "").strip()

    if clean_email:
        merged["email"] = clean_email
        updates_applied.append("email")
    if clean_password:
        merged["password"] = clean_password
        updates_applied.append("password")
    if clean_program_id:
        try:
            merged["program_id"] = int(clean_program_id)
        except ValueError:
            current_state = _load_account_state(account_path)
            return _build_feedback("program_id 必须是整数"), current_state
        updates_applied.append("program_id")

    save_account_config(merged, path_obj)
    new_state = _load_account_state(account_path)
    updated_fields = ", ".join(updates_applied) if updates_applied else "none (kept existing values)"
    message = f"Account saved to {new_state.get('path')}. Updated: {updated_fields}."
    return _build_feedback(message, ok=True), new_state


DEFAULT_PARAM_TEMPLATE = _load_profile_param_template(DEFAULT_PROFILE)
DEFAULT_PROPERTY_TYPES = _extract_property_types(DEFAULT_PARAM_TEMPLATE)
DEFAULT_SELECTED_PROPERTIES = _extract_selected_properties(DEFAULT_PARAM_TEMPLATE)
DEFAULT_INTERACTION_TYPE, DEFAULT_INTERACTION_MODEL, DEFAULT_INTERACTION_ELEMENTS = _extract_interaction_defaults(
    DEFAULT_PARAM_TEMPLATE
)
DEFAULT_ACCOUNT_STATE = _load_account_state()


def _build_param_payload(
    profile: str,
    with_relax: bool,
    selected_properties: List[str],
    interaction_type: str,
    interaction_model: str,
    element_slots: List[str],
    interaction_incar: str = "",
    interaction_rows: List[Dict[str, str]] = None,
    base_template: Dict[str, Any] = None,
) -> Dict[str, Any]:
    template = base_template if isinstance(base_template, dict) and base_template else DEFAULT_PARAM_TEMPLATE
    payload = copy.deepcopy(template)

    if with_relax:
        payload["relaxation"] = copy.deepcopy(template.get("relaxation", {}))
    else:
        payload.pop("relaxation", None)

    selected_set = set(selected_properties or [])
    kept_properties = []
    for item in payload.get("properties", []):
        if not isinstance(item, dict):
            continue
        ptype = item.get("type")
        if ptype in selected_set:
            item["req_calc"] = True
            kept_properties.append(item)
    payload["properties"] = kept_properties

    clean_elements = []
    for ele in element_slots:
        if not ele or not ele.strip():
            continue
        symbol = ele.strip()
        if symbol not in clean_elements:
            clean_elements.append(symbol)

    interaction_rows = interaction_rows or []
    potcar_map = _rows_to_mapping(
        [row.get("element", "") if isinstance(row, dict) else "" for row in interaction_rows],
        [row.get("potcar", "") if isinstance(row, dict) else "" for row in interaction_rows],
    )
    orb_map = _rows_to_mapping(
        [row.get("element", "") if isinstance(row, dict) else "" for row in interaction_rows],
        [row.get("orb_file", "") if isinstance(row, dict) else "" for row in interaction_rows],
    )
    interaction_from_template = payload.get("interaction")
    interaction_payload = copy.deepcopy(interaction_from_template) if isinstance(interaction_from_template, dict) else {}
    template_type = interaction_payload.get("type") if isinstance(interaction_payload, dict) else None
    effective_type = (interaction_type or "").strip() or interaction_payload.get("type") or (
        profile if profile in {"vasp", "abacus"} else "eam_alloy"
    )
    interaction_payload["type"] = effective_type

    if profile == "lammps":
        model_text = (interaction_model or "").strip()
        if model_text:
            if "," in model_text:
                interaction_payload["model"] = [item.strip() for item in model_text.split(",") if item.strip()]
            else:
                interaction_payload["model"] = model_text
        elif "model" in interaction_payload and interaction_payload.get("model") and effective_type == template_type:
            pass
        elif effective_type == "eam_alloy":
            interaction_payload["model"] = "Al.eam.alloy"
        else:
            interaction_payload.pop("model", None)

        if clean_elements:
            interaction_payload["type_map"] = {ele: idx for idx, ele in enumerate(clean_elements)}
        elif (
            isinstance(interaction_payload.get("type_map"), dict)
            and interaction_payload["type_map"]
            and effective_type == template_type
        ):
            pass
        elif effective_type == "eam_alloy":
            interaction_payload["type_map"] = {"Al": 0}
        else:
            interaction_payload.pop("type_map", None)
        interaction_payload.pop("incar", None)
        interaction_payload.pop("potcars", None)
        interaction_payload.pop("potcar_prefix", None)
    else:
        interaction_payload.pop("model", None)
        interaction_payload.pop("type_map", None)
        if interaction_incar.strip():
            interaction_payload["incar"] = interaction_incar.strip()
        if potcar_map:
            interaction_payload["potcars"] = potcar_map
        elif "potcars" in interaction_payload and isinstance(interaction_payload.get("potcars"), dict):
            pass
        else:
            interaction_payload.pop("potcars", None)
        if profile == "abacus":
            if orb_map:
                interaction_payload["orb_files"] = orb_map
            elif "orb_files" in interaction_payload and isinstance(interaction_payload.get("orb_files"), dict):
                pass
            else:
                interaction_payload.pop("orb_files", None)

    payload["interaction"] = interaction_payload

    return payload


def _build_submit_shell_command(param_file: str, global_file: str) -> Tuple[str, str]:
    apex_bin = shutil.which("apex")
    if apex_bin:
        submit_inner = (
            f"{shlex.quote(apex_bin)} submit {shlex.quote(param_file)} -c {shlex.quote(global_file)}"
        )
        display_cmd = DEFAULT_SUBMIT_COMMAND
    else:
        submit_inner = (
            f"{shlex.quote(sys.executable)} -m apex submit {shlex.quote(param_file)} -c {shlex.quote(global_file)}"
        )
        display_cmd = f"nohup {submit_inner} > apex.log 2>&1 &"
    shell_cmd = f"nohup {submit_inner} > apex.log 2>&1 & echo $!"
    return shell_cmd, display_cmd


def _run_submit_in_background(param_file: str, global_file: str) -> Dict[str, Any]:
    shell_cmd, display_cmd = _build_submit_shell_command(param_file, global_file)
    try:
        completed = subprocess.run(
            ["bash", "-lc", shell_cmd],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Failed to start background submit: {exc}",
            "command": display_cmd,
            "returncode": "",
            "stdout": "",
            "stderr": str(exc),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }

    pid = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    message = "Submit started in background."
    if pid:
        message += f" PID: {pid}."
    message += " Saved files: param.json, global.json. Log file: apex.log"

    return {
        "ok": completed.returncode == 0,
        "message": message if completed.returncode == 0 else "Background submit failed to start.",
        "command": display_cmd,
        "returncode": str(completed.returncode),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def _ensure_default_interaction_files(
    profile: str,
    param_payload: Dict[str, Any],
    incar_content: str = None,
) -> List[str]:
    created_paths: List[str] = []
    interaction = param_payload.get("interaction")
    if not isinstance(interaction, dict):
        return created_paths

    incar_value = interaction.get("incar")
    if isinstance(incar_value, str) and incar_value.strip():
        clean_incar = _strip_parenthetical_suffix(incar_value)
        interaction["incar"] = clean_incar
        target_path = os.path.join(os.getcwd(), clean_incar)
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        if incar_content is not None:
            with open(target_path, "w", encoding="utf-8") as f:
                if incar_content and not incar_content.endswith("\n"):
                    f.write(f"{incar_content}\n")
                else:
                    f.write(incar_content or "")
            created_paths.append(clean_incar)
        else:
            source_path = os.path.join(_profile_dir(profile), "param_interaction", clean_incar)
            if os.path.isfile(source_path) and not os.path.exists(target_path):
                shutil.copyfile(source_path, target_path)
                created_paths.append(clean_incar)

    for map_key in ("potcars", "orb_files"):
        value_map = interaction.get(map_key)
        if not isinstance(value_map, dict):
            continue
        interaction[map_key] = {
            str(k): _strip_parenthetical_suffix(str(v)) for k, v in value_map.items()
        }

    return created_paths


def _parse_submit_payloads(submit_global_editor: str, submit_param_editor: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    try:
        global_payload = json.loads(submit_global_editor or "{}")
    except json.JSONDecodeError as exc:
        return {}, {}, _build_feedback(f"global.json JSON 格式错误: {exc}")

    try:
        param_payload = json.loads(submit_param_editor or "{}")
    except json.JSONDecodeError as exc:
        return {}, {}, _build_feedback(f"param.json JSON 格式错误: {exc}")

    if not isinstance(global_payload, dict):
        return {}, {}, _build_feedback("global.json 必须是 JSON object")
    if not isinstance(param_payload, dict):
        return {}, {}, _build_feedback("param.json 必须是 JSON object")
    return global_payload, param_payload, {}


def _write_submit_json_files(global_payload: Dict[str, Any], param_payload: Dict[str, Any]) -> None:
    with open("global.json", "w", encoding="utf-8") as f:
        json.dump(global_payload, f, indent=4, ensure_ascii=False)
        f.write("\n")
    with open("param.json", "w", encoding="utf-8") as f:
        json.dump(param_payload, f, indent=4, ensure_ascii=False)
        f.write("\n")


DEFAULT_GLOBAL_EDITOR_TEXT = _json_dump_text(_load_profile_global(DEFAULT_PROFILE))
DEFAULT_INTERACTION_ROWS = _interaction_table_rows_from_template(DEFAULT_PROFILE, DEFAULT_PARAM_TEMPLATE)
DEFAULT_INTERACTION_INCAR_CONTENT = _load_profile_incar_content(DEFAULT_PROFILE, DEFAULT_PARAM_TEMPLATE)
DEFAULT_PARAM_EDITOR_TEXT = _json_dump_text(
    _build_param_payload(
        profile=DEFAULT_PROFILE,
        with_relax="relaxation" in DEFAULT_PARAM_TEMPLATE,
        selected_properties=DEFAULT_SELECTED_PROPERTIES,
        interaction_type=DEFAULT_INTERACTION_TYPE,
        interaction_model=DEFAULT_INTERACTION_MODEL,
        element_slots=DEFAULT_INTERACTION_ELEMENTS,
        interaction_incar=_extract_interaction_incar(DEFAULT_PARAM_TEMPLATE),
        interaction_rows=DEFAULT_INTERACTION_ROWS,
        base_template=DEFAULT_PARAM_TEMPLATE,
    )
)


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
        property_options = [{"label": name, "value": name} for name in DEFAULT_PROPERTY_TYPES]
        interaction_options = _interaction_type_options_for_profile(DEFAULT_PROFILE, DEFAULT_INTERACTION_TYPE)

        return dbc.Tab(
            label="Submit",
            children=[
                html.P("只保留提交相关配置：选择模板 + 填写 interaction + 勾选计算项。", className="text-muted"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H5("基础设置"),
                                dbc.Label("计算后端模板 (global.json)"),
                                dcc.Dropdown(
                                    id="submit-profile",
                                    clearable=False,
                                    value=DEFAULT_PROFILE,
                                    options=[
                                        {"label": "LAMMPS", "value": "lammps"},
                                        {"label": "VASP", "value": "vasp"},
                                        {"label": "ABACUS", "value": "abacus"},
                                    ],
                                ),
                                html.Br(),
                                dbc.Label("是否计算 Relax"),
                                dcc.Checklist(
                                    id="submit-relax-check",
                                    options=[{"label": "启用 relaxation", "value": "relax"}],
                                    value=["relax"],
                                    inputStyle={"marginRight": "6px", "marginLeft": "10px"},
                                    labelStyle={"display": "inline-block"},
                                ),
                                html.Br(),
                                dbc.Label("Properties 勾选"),
                                dcc.Checklist(
                                    id="submit-properties-check",
                                    options=property_options,
                                    value=DEFAULT_SELECTED_PROPERTIES,
                                    inputStyle={"marginRight": "6px", "marginLeft": "10px"},
                                    labelStyle={"display": "inline-block", "marginRight": "12px"},
                                ),
                                html.Br(),
                                dbc.Label("interaction.type"),
                                dcc.Dropdown(
                                    id="submit-interaction-type",
                                    clearable=False,
                                    value=DEFAULT_INTERACTION_TYPE,
                                    options=interaction_options,
                                ),
                                html.Br(),
                                html.Div(
                                    id="submit-lammps-interaction-block",
                                    style={"display": "block"},
                                    children=[
                                        dbc.Label("interaction.model"),
                                        dbc.Input(
                                            id="submit-interaction-model",
                                            value=DEFAULT_INTERACTION_MODEL,
                                            placeholder="Al.eam.alloy",
                                        ),
                                        html.Br(),
                                        dbc.Label("interaction.type_map 元素 (按顺序自动编号 0,1,2...)"),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Input(
                                                        id="submit-element-1",
                                                        value=DEFAULT_INTERACTION_ELEMENTS[0] if len(DEFAULT_INTERACTION_ELEMENTS) > 0 else "",
                                                        placeholder="Al",
                                                    ),
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Input(
                                                        id="submit-element-2",
                                                        value=DEFAULT_INTERACTION_ELEMENTS[1] if len(DEFAULT_INTERACTION_ELEMENTS) > 1 else "",
                                                        placeholder="",
                                                    ),
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Input(
                                                        id="submit-element-3",
                                                        value=DEFAULT_INTERACTION_ELEMENTS[2] if len(DEFAULT_INTERACTION_ELEMENTS) > 2 else "",
                                                        placeholder="",
                                                    ),
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Input(
                                                        id="submit-element-4",
                                                        value=DEFAULT_INTERACTION_ELEMENTS[3] if len(DEFAULT_INTERACTION_ELEMENTS) > 3 else "",
                                                        placeholder="",
                                                    ),
                                                    md=3,
                                                ),
                                            ],
                                            className="g-2",
                                        ),
                                        html.Br(),
                                        dbc.Label("更多元素（预留接口，逗号/空格分隔）"),
                                        dbc.Input(
                                            id="submit-element-extra",
                                            value=", ".join(DEFAULT_INTERACTION_ELEMENTS[4:]),
                                            placeholder="例如: Cu, Ni, Fe, Cr",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="submit-electronic-interaction-block",
                                    style={"display": "none"},
                                    children=[
                                        dbc.Label("interaction 列表（动态增删行）"),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Button("加一行", id="submit-row-add", color="secondary", className="me-2"),
                                                    width="auto",
                                                ),
                                                dbc.Col(
                                                    dbc.Button("删一行", id="submit-row-del", color="secondary"),
                                                    width="auto",
                                                ),
                                            ],
                                            className="g-2 mb-2",
                                        ),
                                        html.Small(
                                            "VASP: Element + POTCAR；ABACUS: Element + POTCAR + ORB",
                                            className="text-muted",
                                        ),
                                        dash_table.DataTable(
                                            id="submit-interaction-table",
                                            columns=_interaction_table_columns_for_profile(DEFAULT_PROFILE),
                                            data=DEFAULT_INTERACTION_ROWS,
                                            editable=True,
                                            row_deletable=True,
                                            style_table={"overflowX": "auto"},
                                            style_cell={"textAlign": "left", "padding": "6px"},
                                        ),
                                    ],
                                ),
                                html.Br(),
                                dbc.Button("Reset", id="submit-reset", color="secondary", className="me-2"),
                                dbc.Button("Apply", id="submit-apply", color="secondary", className="me-2"),
                                dbc.Button("Submit", id="submit-run", color="primary"),
                            ],
                            md=5,
                        ),
                        dbc.Col(
                            [
                                html.H5("Advanced Setting"),
                                dbc.Label("global.json 编辑区"),
                                dcc.Textarea(
                                    id="submit-global-editor",
                                    value=DEFAULT_GLOBAL_EDITOR_TEXT,
                                    style={"width": "100%", "height": "220px", "fontFamily": "monospace"},
                                ),
                                html.Div(
                                    id="submit-incar-right-block",
                                    style={"display": "none"},
                                    children=[
                                        html.Br(),
                                        dbc.Label("interaction.incar (会自动去掉括号备注)"),
                                        dbc.Input(
                                            id="submit-interaction-incar",
                                            value=_extract_interaction_incar(DEFAULT_PARAM_TEMPLATE),
                                            placeholder="vasp_input/INCAR",
                                        ),
                                        html.Br(),
                                        dbc.Label(id="submit-incar-editor-title", children=_interaction_editor_label(DEFAULT_PROFILE)),
                                        dcc.Textarea(
                                            id="submit-incar-content",
                                            value=DEFAULT_INTERACTION_INCAR_CONTENT,
                                            style={"width": "100%", "height": "180px", "fontFamily": "monospace"},
                                        ),
                                    ],
                                ),
                                html.Br(),
                                dbc.Label("param.json 编辑区"),
                                dcc.Textarea(
                                    id="submit-param-editor",
                                    value=DEFAULT_PARAM_EDITOR_TEXT,
                                    style={"width": "100%", "height": "300px", "fontFamily": "monospace"},
                                ),
                            ],
                            md=7,
                        ),
                    ],
                    className="g-3",
                ),
                html.Br(),
                dbc.Label("运行命令 (Run submit 后后台执行)"),
                html.Pre(
                    id="submit-command-preview",
                    children=DEFAULT_SUBMIT_COMMAND,
                    style={"backgroundColor": "#f5f5f5", "padding": "10px", "borderRadius": "4px"},
                ),
            ],
        )

    @staticmethod
    def _build_manage_tab() -> dbc.Tab:
        return dbc.Tab(
            label="Manage",
            children=[
                html.P("Manage 仅保留 apex.log 查看。", className="text-muted"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Button("刷新日志", id="manage-log-refresh", color="primary", className="me-2"),
                                dcc.Interval(id="manage-log-interval", interval=3000, n_intervals=0),
                                html.Small("每 3 秒自动刷新一次", className="text-muted"),
                            ],
                            md=12,
                        ),
                    ]
                ),
                html.Br(),
                html.Pre(
                    id="manage-log-content",
                    style={
                        "whiteSpace": "pre-wrap",
                        "backgroundColor": "#0b0b0b",
                        "color": "#cfe6cf",
                        "padding": "12px",
                        "borderRadius": "6px",
                        "maxHeight": "560px",
                        "overflowY": "auto",
                    },
                    children=_read_log_tail(),
                ),
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

    @staticmethod
    def _build_account_tab() -> dbc.Tab:
        return dbc.Tab(
            label="Account",
            children=[
                html.P("底层对应 `apex account`，密码仅支持覆盖保存，不会在界面显示。", className="text-muted"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Bohrium Email / 用户名"),
                                dbc.Input(
                                    id="account-email",
                                    value=DEFAULT_ACCOUNT_STATE.get("email", ""),
                                    placeholder="you@example.com",
                                ),
                                html.Br(),
                                dbc.Label("Program ID"),
                                dbc.Input(
                                    id="account-program-id",
                                    value=DEFAULT_ACCOUNT_STATE.get("program_id", ""),
                                    placeholder="例如 1234",
                                ),
                                html.Br(),
                                dbc.Label("Password (留空表示保持当前密码不变)"),
                                dbc.Input(
                                    id="account-password",
                                    type="password",
                                    value="",
                                    placeholder="输入新密码以覆盖",
                                ),
                                html.Br(),
                                dbc.Button("刷新", id="account-refresh", color="secondary", className="me-2"),
                                dbc.Button("覆盖保存", id="account-save", color="primary"),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("当前账号信息"),
                                html.Pre(
                                    id="account-summary",
                                    children=_render_account_summary(DEFAULT_ACCOUNT_STATE),
                                    style={"backgroundColor": "#f5f5f5", "padding": "10px", "borderRadius": "4px"},
                                ),
                                dbc.Label("操作结果"),
                                html.Pre(
                                    id="account-feedback",
                                    children="",
                                    style={
                                        "whiteSpace": "pre-wrap",
                                        "backgroundColor": "#111",
                                        "color": "#f5f5f5",
                                        "padding": "10px",
                                        "borderRadius": "4px",
                                        "minHeight": "80px",
                                    },
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    className="g-3",
                ),
            ],
        )

    def _build_layout(self) -> dbc.Container:
        return dbc.Container(
            [
                html.H2("APEX Graphical Interface", className="mt-3"),
                html.P(
                    "Submit 页已简化为 param.json/global.json 生成与后台提交。",
                    className="text-muted",
                ),
                dcc.Store(id="command-result"),
                dcc.ConfirmDialog(id="submit-confirm-dialog"),
                dbc.Tabs(
                    [
                        self._build_submit_tab(),
                        self._build_manage_tab(),
                        self._build_advanced_tab(),
                        self._build_account_tab(),
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
            Output("submit-global-editor", "value"),
            Output("submit-relax-check", "value"),
            Output("submit-properties-check", "options"),
            Output("submit-properties-check", "value"),
            Output("submit-interaction-type", "options"),
            Output("submit-interaction-type", "value"),
            Output("submit-lammps-interaction-block", "style"),
            Output("submit-electronic-interaction-block", "style"),
            Output("submit-incar-right-block", "style"),
            Output("submit-interaction-model", "value"),
            Output("submit-interaction-incar", "value"),
            Output("submit-incar-editor-title", "children"),
            Output("submit-incar-content", "value"),
            Output("submit-element-1", "value"),
            Output("submit-element-2", "value"),
            Output("submit-element-3", "value"),
            Output("submit-element-4", "value"),
            Output("submit-element-extra", "value"),
            Output("submit-interaction-table", "columns"),
            Input("submit-profile", "value"),
        )
        def _sync_profile_defaults(profile):
            param_template = _load_profile_param_template(profile)
            prop_types = _extract_property_types(param_template)
            prop_selected = _extract_selected_properties(param_template)
            interaction_type, interaction_model, interaction_elements = _extract_interaction_defaults(param_template)
            interaction_incar = _extract_interaction_incar(param_template)
            interaction_incar_content = _load_profile_incar_content(profile, param_template)
            global_payload = _load_profile_global(profile)
            prop_options = [{"label": name, "value": name} for name in prop_types]
            interaction_options = _interaction_type_options_for_profile(profile, interaction_type)
            relax_value = ["relax"] if "relaxation" in param_template else []
            lammps_style = {"display": "block"} if profile == "lammps" else {"display": "none"}
            electronic_style = {"display": "none"} if profile == "lammps" else {"display": "block"}
            table_columns = _interaction_table_columns_for_profile(profile)

            return (
                _json_dump_text(global_payload),
                relax_value,
                prop_options,
                prop_selected,
                interaction_options,
                interaction_type,
                lammps_style,
                electronic_style,
                electronic_style,
                interaction_model,
                interaction_incar,
                _interaction_editor_label(profile),
                interaction_incar_content,
                interaction_elements[0] if len(interaction_elements) > 0 else "",
                interaction_elements[1] if len(interaction_elements) > 1 else "",
                interaction_elements[2] if len(interaction_elements) > 2 else "",
                interaction_elements[3] if len(interaction_elements) > 3 else "",
                ", ".join(interaction_elements[4:]),
                table_columns,
            )

        @self.app.callback(
            Output("submit-interaction-table", "data"),
            Input("submit-profile", "value"),
            Input("submit-row-add", "n_clicks"),
            Input("submit-row-del", "n_clicks"),
            State("submit-interaction-table", "data"),
            State("submit-interaction-table", "columns"),
            prevent_initial_call=True,
        )
        def _update_interaction_table(profile, _add_clicks, _del_clicks, current_data, columns):
            triggered_id = _resolve_triggered_id()

            if triggered_id == "submit-profile":
                template = _load_profile_param_template(profile)
                return _interaction_table_rows_from_template(profile, template)

            rows = copy.deepcopy(current_data or [])
            columns = columns or _interaction_table_columns_for_profile(profile)
            column_ids = [col.get("id") for col in columns if isinstance(col, dict)]
            blank_row = {key: "" for key in column_ids}

            if triggered_id == "submit-row-add":
                rows.append(blank_row)
            elif triggered_id == "submit-row-del":
                if rows:
                    rows.pop()

            if not rows:
                rows = [blank_row]
            return rows

        @self.app.callback(
            Output("submit-param-editor", "value"),
            Input("submit-profile", "value"),
            Input("submit-reset", "n_clicks"),
            Input("submit-relax-check", "value"),
            Input("submit-properties-check", "value"),
            State("submit-profile", "value"),
            State("submit-interaction-type", "value"),
            State("submit-interaction-model", "value"),
            State("submit-interaction-incar", "value"),
            State("submit-element-1", "value"),
            State("submit-element-2", "value"),
            State("submit-element-3", "value"),
            State("submit-element-4", "value"),
            State("submit-element-extra", "value"),
            State("submit-interaction-table", "data"),
            prevent_initial_call=True,
        )
        def _generate_param_editor(
            profile_input,
            _reset_clicks,
            relax_check,
            properties_check,
            profile_state,
            interaction_type,
            interaction_model,
            interaction_incar,
            ele1,
            ele2,
            ele3,
            ele4,
            ele_extra,
            interaction_table_rows,
        ):
            triggered_id = _resolve_triggered_id()
            profile = profile_state or profile_input or DEFAULT_PROFILE
            param_template = _load_profile_param_template(profile)

            if triggered_id in {"submit-profile", "submit-reset", "submit-relax-check", "submit-properties-check"}:
                init_interaction_type, init_interaction_model, init_elements = _extract_interaction_defaults(param_template)
                selected_props = (
                    _extract_selected_properties(param_template)
                    if triggered_id == "submit-profile"
                    else (properties_check or [])
                )
                enable_relax = (
                    "relaxation" in param_template
                    if triggered_id == "submit-profile"
                    else ("relax" in (relax_check or []))
                )
                if triggered_id == "submit-profile":
                    next_interaction_type = init_interaction_type
                    next_interaction_model = init_interaction_model
                    next_elements = init_elements
                    next_interaction_incar = _extract_interaction_incar(param_template)
                    next_interaction_rows = _interaction_table_rows_from_template(profile, param_template)
                else:
                    next_interaction_type = interaction_type or init_interaction_type
                    next_interaction_model = interaction_model or init_interaction_model
                    next_elements = [
                        ele1 or "",
                        ele2 or "",
                        ele3 or "",
                        ele4 or "",
                        *_parse_extra_elements(ele_extra or ""),
                    ]
                    next_interaction_incar = interaction_incar or _extract_interaction_incar(param_template)
                    next_interaction_rows = interaction_table_rows or _interaction_table_rows_from_template(
                        profile, param_template
                    )
                payload = _build_param_payload(
                    profile=profile,
                    with_relax=enable_relax,
                    selected_properties=selected_props,
                    interaction_type=next_interaction_type,
                    interaction_model=next_interaction_model,
                    element_slots=next_elements,
                    interaction_incar=next_interaction_incar,
                    interaction_rows=next_interaction_rows,
                    base_template=param_template,
                )
                return _json_dump_text(payload)

            all_elements = [
                ele1 or "",
                ele2 or "",
                ele3 or "",
                ele4 or "",
                *_parse_extra_elements(ele_extra or ""),
            ]
            payload = _build_param_payload(
                profile=profile,
                with_relax="relax" in (relax_check or []),
                selected_properties=properties_check or [],
                interaction_type=interaction_type or "eam_alloy",
                interaction_model=interaction_model or "",
                element_slots=all_elements,
                interaction_incar=interaction_incar or "",
                interaction_rows=interaction_table_rows or [],
                base_template=param_template,
            )
            return _json_dump_text(payload)

        @self.app.callback(
            Output("command-result", "data"),
            Output("submit-confirm-dialog", "displayed"),
            Output("submit-confirm-dialog", "message"),
            Input("submit-apply", "n_clicks"),
            Input("submit-run", "n_clicks"),
            Input("submit-confirm-dialog", "submit_n_clicks"),
            Input("advanced-run", "n_clicks"),
            State("submit-profile", "value"),
            State("submit-global-editor", "value"),
            State("submit-param-editor", "value"),
            State("submit-incar-content", "value"),
            State("advanced-command", "value"),
            prevent_initial_call=True,
        )
        def _handle_command(
            _apply_clicks,
            _submit_clicks,
            _submit_confirm_clicks,
            _advanced_clicks,
            submit_profile,
            submit_global_editor,
            submit_param_editor,
            submit_incar_content,
            advanced_command,
        ):
            triggered_id = _resolve_triggered_id()
            default_confirm_message = "检测到已存在 apex.log，是否确认重新提交？"
            profile = submit_profile if submit_profile in PROFILE_NAMES else DEFAULT_PROFILE

            if triggered_id in {"submit-apply", "submit-run", "submit-confirm-dialog"}:
                global_payload, param_payload, parse_feedback = _parse_submit_payloads(
                    submit_global_editor,
                    submit_param_editor,
                )
                if parse_feedback:
                    return parse_feedback, False, default_confirm_message

                created_files = _ensure_default_interaction_files(
                    profile,
                    param_payload,
                    incar_content=submit_incar_content,
                )
                _write_submit_json_files(global_payload, param_payload)

                if triggered_id == "submit-apply":
                    message = "Applied: saved global.json and param.json."
                    if created_files:
                        message += " Saved interaction files: " + ", ".join(created_files)
                    return _build_feedback(message=message, ok=True), False, default_confirm_message

            if triggered_id == "submit-run":
                if os.path.exists("apex.log"):
                    warning = _build_feedback(
                        "Detected existing apex.log. Please confirm resubmission.",
                        ok=False,
                    )
                    return warning, True, default_confirm_message

                run_feedback = _run_submit_in_background("param.json", "global.json")
                if created_files:
                    extra_line = " Auto-created default files: " + ", ".join(created_files)
                    run_feedback["message"] = f"{run_feedback.get('message', '').rstrip()}{extra_line}"
                return run_feedback, False, default_confirm_message

            if triggered_id == "submit-confirm-dialog":
                run_feedback = _run_submit_in_background("param.json", "global.json")
                if created_files:
                    extra_line = " Auto-created default files: " + ", ".join(created_files)
                    run_feedback["message"] = f"{run_feedback.get('message', '').rstrip()}{extra_line}"
                return run_feedback, False, default_confirm_message

            if triggered_id == "advanced-run":
                if not advanced_command or not advanced_command.strip():
                    return _build_feedback("Please provide a command tail."), False, default_confirm_message
                try:
                    advanced_args = shlex.split(advanced_command.strip())
                except ValueError as exc:
                    return _build_feedback(f"Command parse error: {exc}"), False, default_confirm_message
                if advanced_args and advanced_args[0] == "apex":
                    advanced_args = advanced_args[1:]
                if not advanced_args:
                    return _build_feedback("Please provide arguments after `apex`."), False, default_confirm_message
                if advanced_args[0] in BLOCKED_INLINE_COMMANDS:
                    return (
                        _build_feedback(
                            f"`apex {advanced_args[0]}` is blocked in Advanced mode to avoid nested Dash apps."
                        ),
                        False,
                        default_confirm_message,
                    )
                return _run_apex_command(advanced_args), False, default_confirm_message

            return _build_feedback("No action detected."), False, default_confirm_message

        @self.app.callback(
            Output("account-email", "value"),
            Output("account-program-id", "value"),
            Output("account-password", "value"),
            Output("account-summary", "children"),
            Output("account-feedback", "children"),
            Input("account-refresh", "n_clicks"),
            Input("account-save", "n_clicks"),
            State("account-email", "value"),
            State("account-program-id", "value"),
            State("account-password", "value"),
            prevent_initial_call=True,
        )
        def _handle_account(_refresh_clicks, _save_clicks, email_value, program_id_value, password_value):
            triggered_id = _resolve_triggered_id()
            if triggered_id == "account-save":
                feedback, account_state = _save_account_overwrite(
                    email=email_value or "",
                    password=password_value or "",
                    program_id_text=program_id_value or "",
                )
            else:
                account_state = _load_account_state()
                feedback = _build_feedback("Account info refreshed.", ok=True)
            return (
                account_state.get("email", ""),
                account_state.get("program_id", ""),
                "",
                _render_account_summary(account_state),
                _brief_feedback(feedback),
            )

        @self.app.callback(Output("command-output", "children"), Input("command-result", "data"))
        def _render_output(payload):
            return _format_feedback(payload)

        @self.app.callback(
            Output("manage-log-content", "children"),
            Input("manage-log-refresh", "n_clicks"),
            Input("manage-log-interval", "n_intervals"),
        )
        def _update_manage_log(_clicks, _n_intervals):
            return _read_log_tail()

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
