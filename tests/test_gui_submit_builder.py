import base64
import io
import json
import os
import tempfile
import unittest
import zipfile

from apex.gui import (
    _autodetect_interaction_rows,
    _build_param_payload,
    _cleanup_reset_logs,
    _ensure_default_interaction_files,
    _extract_property_types,
    _extract_potcar_rows,
    _parse_extra_elements,
    _interaction_editor_label,
    _interaction_table_columns_for_profile,
    _interaction_table_rows_from_template,
    _interaction_type_options_for_profile,
    _list_structure_path_options,
    _list_workdir_file_options,
    _load_account_state,
    _load_profile_param_template,
    _parse_submit_payloads,
    _read_latest_workflow_id,
    _render_account_summary,
    _save_uploaded_files,
    _save_account_overwrite,
    _strip_parenthetical_suffix,
    _summarize_step_progress,
)


class TestGuiSubmitBuilder(unittest.TestCase):
    def test_build_param_payload_sets_interaction_and_req_calc(self):
        payload = _build_param_payload(
            profile="lammps",
            selected_structures=["confs/std-fcc"],
            with_relax=False,
            selected_properties=["elastic", "eos"],
            interaction_type="eam_alloy",
            interaction_model="my_model.eam",
            element_slots=["Al", "Ni", "", ""],
        )

        self.assertNotIn("relaxation", payload)
        self.assertEqual(payload["structures"], ["confs/std-fcc"])
        self.assertEqual(payload["interaction"]["type"], "eam_alloy")
        self.assertEqual(payload["interaction"]["model"], "my_model.eam")
        self.assertEqual(payload["interaction"]["type_map"], "auto")

        req_calc = {
            item["type"]: item.get("req_calc")
            for item in payload.get("properties", [])
            if isinstance(item, dict) and "type" in item
        }
        self.assertTrue(req_calc.get("elastic"))
        self.assertTrue(req_calc.get("eos"))
        if "vacancy" in req_calc:
            self.assertFalse(req_calc["vacancy"])

    def test_build_param_payload_default_element_and_model(self):
        payload = _build_param_payload(
            profile="lammps",
            selected_structures=["confs/std-bcc"],
            with_relax=True,
            selected_properties=[],
            interaction_type="deepmd",
            interaction_model="",
            element_slots=["", "", "", ""],
        )

        self.assertIn("relaxation", payload)
        self.assertEqual(payload["interaction"]["type"], "deepmd")
        self.assertNotIn("model", payload["interaction"])
        self.assertEqual(payload["interaction"]["type_map"], "auto")

    def test_parse_extra_elements(self):
        parsed = _parse_extra_elements("Cu, Ni Fe;Cr\nMn")
        self.assertEqual(parsed, ["Cu", "Ni", "Fe", "Cr", "Mn"])

    def test_list_workdir_file_options_recurses_and_keeps_current(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "models"), exist_ok=True)
            with open(os.path.join(tmpdir, "models", "Ni.eam.alloy"), "w", encoding="utf-8") as f:
                f.write("eam")
            options = _list_workdir_file_options(tmpdir, "missing.pb")
            values = [item["value"] for item in options]
            self.assertIn("models/Ni.eam.alloy", values)
            self.assertEqual(values[0], "missing.pb")

    def test_list_structure_path_options_returns_structure_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "confs", "std-bcc"), exist_ok=True)
            with open(os.path.join(tmpdir, "confs", "std-bcc", "POSCAR"), "w", encoding="utf-8") as f:
                f.write("POSCAR")
            options = _list_structure_path_options(tmpdir, ["confs/std-*"])
            values = [item["value"] for item in options]
            self.assertIn("confs/std-bcc", values)
            self.assertEqual(values[0], "confs/std-*")

    def test_build_param_payload_ignores_manual_elements_for_auto_type_map(self):
        payload = _build_param_payload(
            profile="lammps",
            selected_structures=["confs/std-hcp"],
            with_relax=True,
            selected_properties=[],
            interaction_type="eam_alloy",
            interaction_model="x",
            element_slots=["Al", "Ni", "Al", "Cu", "Ni"],
        )
        self.assertEqual(payload["interaction"]["type_map"], "auto")

    def test_profile_templates_have_different_property_options(self):
        lammps = _extract_property_types(_load_profile_param_template("lammps"))
        vasp = _extract_property_types(_load_profile_param_template("vasp"))
        abacus = _extract_property_types(_load_profile_param_template("abacus"))

        self.assertIn("cohesive", lammps)
        self.assertNotIn("cohesive", vasp)
        self.assertIn("phonon", vasp)
        self.assertIn("phonon", abacus)
        self.assertNotIn("phonon", lammps)
        self.assertIn("gamma_surface", lammps)
        self.assertIn("gamma_surface", vasp)
        self.assertIn("gamma_surface", abacus)

    def test_lammps_interaction_types_exclude_vasp_abacus(self):
        options = [item["value"] for item in _interaction_type_options_for_profile("lammps", "meam")]
        self.assertNotIn("vasp", options)
        self.assertNotIn("abacus", options)
        self.assertIn("meam", options)

    def test_profile_template_merges_param_interaction(self):
        vasp_template = _load_profile_param_template("vasp")
        self.assertEqual(vasp_template["interaction"]["type"], "vasp")
        self.assertIn("potcars", vasp_template["interaction"])
        self.assertIn("incar", vasp_template["interaction"])
        pot_rows = _extract_potcar_rows(vasp_template)
        self.assertTrue(pot_rows and "(to be change)" not in pot_rows[0][1])

    def test_abacus_interaction_supports_orb_files(self):
        abacus_template = _load_profile_param_template("abacus")
        rows = _interaction_table_rows_from_template("abacus", abacus_template)
        payload = _build_param_payload(
            profile="abacus",
            selected_structures=["confs/fcc-Al"],
            with_relax=True,
            selected_properties=[],
            interaction_type="abacus",
            interaction_model="",
            element_slots=[],
            interaction_incar="abacus_input/INPUT(defaule value)",
            interaction_rows=rows,
            base_template=abacus_template,
        )
        self.assertIn("input", payload["interaction"])
        self.assertNotIn("incar", payload["interaction"])
        self.assertIn("orb_files", payload["interaction"])
        self.assertIn("potcars", payload["interaction"])

    def test_autodetect_interaction_rows_for_vasp_uses_poscar_order_and_suffix(self):
        vasp_template = _load_profile_param_template("vasp")
        poscar_text = "Test\n1.0\n1 0 0\n0 1 0\n0 0 1\nMo Al\n1 1\nDirect\n0 0 0\n0.5 0.5 0.5\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "confs", "std-bcc"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "vasp_input"), exist_ok=True)
            with open(os.path.join(tmpdir, "confs", "std-bcc", "POSCAR"), "w", encoding="utf-8") as f:
                f.write(poscar_text)
            with open(os.path.join(tmpdir, "vasp_input", "POTCAR.Mo"), "w", encoding="utf-8") as f:
                f.write("Mo")
            rows = _autodetect_interaction_rows("vasp", tmpdir, ["confs/std-bcc"], vasp_template)
            self.assertEqual(rows[0]["element"], "Mo")
            self.assertEqual(rows[0]["potcar"], "POTCAR.Mo")
            self.assertEqual(rows[1]["element"], "Al")
            self.assertIn("请提交对应元素的POTCAR", rows[1]["potcar"])

    def test_autodetect_interaction_rows_for_abacus_uses_prefix(self):
        abacus_template = _load_profile_param_template("abacus")
        poscar_text = "Test\n1.0\n1 0 0\n0 1 0\n0 0 1\nAl H\n1 1\nDirect\n0 0 0\n0.5 0.5 0.5\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "confs", "std-bcc"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "abacus_input"), exist_ok=True)
            with open(os.path.join(tmpdir, "confs", "std-bcc", "POSCAR"), "w", encoding="utf-8") as f:
                f.write(poscar_text)
            with open(os.path.join(tmpdir, "abacus_input", "Al_ONCV_PBE.upf"), "w", encoding="utf-8") as f:
                f.write("Al")
            with open(os.path.join(tmpdir, "abacus_input", "Al_gga_9au.orb"), "w", encoding="utf-8") as f:
                f.write("Al")
            rows = _autodetect_interaction_rows("abacus", tmpdir, ["confs/std-bcc"], abacus_template)
            self.assertEqual(rows[0]["element"], "Al")
            self.assertEqual(rows[0]["potcar"], "Al_ONCV_PBE.upf")
            self.assertEqual(rows[0]["orb_file"], "Al_gga_9au.orb")
            self.assertEqual(rows[1]["element"], "H")
            self.assertIn("请提交对应元素的POTCAR", rows[1]["potcar"])
            self.assertIn("请提交对应元素的ORB", rows[1]["orb_file"])

    def test_interaction_table_columns_profile_specific(self):
        lammps_cols = _interaction_table_columns_for_profile("lammps")
        abacus_cols = _interaction_table_columns_for_profile("abacus")
        self.assertEqual(len(lammps_cols), 2)
        self.assertEqual(len(abacus_cols), 3)

    def test_strip_parenthetical_suffix(self):
        cleaned = _strip_parenthetical_suffix("POTCAR.Mo (to be change)")
        self.assertEqual(cleaned, "POTCAR.Mo")

    def test_ensure_default_interaction_files_for_vasp(self):
        payload = {
            "interaction": {
                "type": "vasp",
                "incar": "vasp_input/INCAR (use default value)",
                "potcars": {"Mo": "POTCAR.Mo (to be change)"},
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                created = _ensure_default_interaction_files("vasp", payload)
                self.assertIn("vasp_input/INCAR", created)
                self.assertTrue(os.path.isfile("vasp_input/INCAR"))
            finally:
                os.chdir(cwd)

    def test_ensure_default_interaction_files_writes_editor_content(self):
        payload = {
            "interaction": {
                "type": "abacus",
                "input": "abacus_input/INPUT(defaule value)",
            }
        }
        custom_content = "INPUT_PARAMETERS\ncustom_key custom_value\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                created = _ensure_default_interaction_files("abacus", payload, incar_content=custom_content)
                self.assertIn("abacus_input/INPUT", created)
                with open("abacus_input/INPUT", "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertEqual(content, custom_content)
            finally:
                os.chdir(cwd)

    def test_interaction_editor_label(self):
        self.assertEqual(_interaction_editor_label("vasp"), "INCAR 编辑区")
        self.assertEqual(_interaction_editor_label("abacus"), "INPUT 编辑区")

    def test_account_overwrite_hides_password_in_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            account_path = os.path.join(tmpdir, "account.json")
            feedback, account_state = _save_account_overwrite(
                email="user@example.com",
                password="secret-password",
                program_id_text="1234",
                account_path=account_path,
            )
            self.assertTrue(feedback["ok"])
            self.assertEqual(account_state["email"], "user@example.com")
            self.assertEqual(account_state["program_id"], "1234")
            self.assertTrue(account_state["password_set"])

            summary = _render_account_summary(account_state)
            self.assertIn("Email: user@example.com", summary)
            self.assertIn("Program ID: 1234", summary)
            self.assertIn("Password: 已设置", summary)
            self.assertNotIn("secret-password", summary)

            with open(account_path, "r", encoding="utf-8") as f:
                on_disk = json.load(f)
            self.assertEqual(on_disk["password"], "secret-password")

    def test_account_overwrite_requires_integer_program_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            account_path = os.path.join(tmpdir, "account.json")
            feedback, account_state = _save_account_overwrite(
                email="user@example.com",
                password="",
                program_id_text="12ab",
                account_path=account_path,
            )
            self.assertFalse(feedback["ok"])
            self.assertIn("program_id", feedback["message"])
            self.assertEqual(account_state["email"], "")
            self.assertEqual(account_state["program_id"], "")

    def test_load_account_state_from_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            account_path = os.path.join(tmpdir, "account.json")
            state = _load_account_state(account_path)
            self.assertEqual(state["email"], "")
            self.assertEqual(state["program_id"], "")
            self.assertFalse(state["password_set"])

    def test_read_latest_workflow_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, ".workflow.log"), "w", encoding="utf-8") as f:
                f.write("wf-old\tsubmit\t2026-01-01T00:00:00\t/tmp/old\n")
                f.write("wf-new\tretrieve\t2026-01-01T00:00:01\t/tmp/new\n")
            self.assertEqual(_read_latest_workflow_id(tmpdir), "wf-new")

    def test_parse_submit_payloads_rejects_dot_in_structures(self):
        global_text = json.dumps({})
        param_text = json.dumps({"structures": ["."], "interaction": {"type": "eam_alloy"}})
        _global_payload, _param_payload, feedback = _parse_submit_payloads(global_text, param_text)
        self.assertIn("dflow does not allow '.' in `structures`", feedback["message"])
        self.assertIn("parameter[0].structures[0] = .", feedback["message"])

    def test_cleanup_reset_logs_removes_requested_files_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["dpdispatcher.log", ".workflow.log", "apex.log", "keep.log"]:
                with open(os.path.join(tmpdir, name), "w", encoding="utf-8") as f:
                    f.write("x")
            removed = _cleanup_reset_logs(tmpdir)
            self.assertEqual(removed, ["dpdispatcher.log", ".workflow.log", "apex.log"])
            self.assertFalse(os.path.exists(os.path.join(tmpdir, "dpdispatcher.log")))
            self.assertFalse(os.path.exists(os.path.join(tmpdir, ".workflow.log")))
            self.assertFalse(os.path.exists(os.path.join(tmpdir, "apex.log")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "keep.log")))

    def test_save_uploaded_files_writes_to_workdir(self):
        payload = base64.b64encode(b"MODEL DATA\n").decode("ascii")
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = _save_uploaded_files([f"data:application/octet-stream;base64,{payload}"], ["model.pb"], tmpdir)
            self.assertEqual(saved, ["confs/model.pb"])
            with open(os.path.join(tmpdir, "confs", "model.pb"), "rb") as f:
                self.assertEqual(f.read(), b"MODEL DATA\n")

    def test_save_uploaded_files_to_workdir_root(self):
        payload = base64.b64encode(b"INPUT\n").decode("ascii")
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = _save_uploaded_files(
                [f"data:text/plain;base64,{payload}"],
                ["global.json"],
                tmpdir,
                target_subdir="",
            )
            self.assertEqual(saved, ["global.json"])
            with open(os.path.join(tmpdir, "global.json"), "rb") as f:
                self.assertEqual(f.read(), b"INPUT\n")

    def test_save_uploaded_files_creates_confs_and_nested_paths(self):
        payload = base64.b64encode(b"POSCAR\n").decode("ascii")
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = _save_uploaded_files(
                [f"data:text/plain;base64,{payload}"],
                ["std-bcc/POSCAR"],
                tmpdir,
            )
            self.assertEqual(saved, ["confs/std-bcc/POSCAR"])
            with open(os.path.join(tmpdir, "confs", "std-bcc", "POSCAR"), "rb") as f:
                self.assertEqual(f.read(), b"POSCAR\n")

    def test_save_uploaded_files_rejects_path_filenames(self):
        payload = base64.b64encode(b"bad").decode("ascii")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                _save_uploaded_files(f"data:text/plain;base64,{payload}", "../bad.txt", tmpdir)

    def test_save_uploaded_files_extracts_zip_folder(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, mode="w") as zf:
            zf.writestr("my-folder/POSCAR", "POSCAR\n")
            zf.writestr("my-folder/sub/INPUT", "INPUT\n")
        payload = base64.b64encode(stream.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmpdir:
            saved = _save_uploaded_files(
                [f"data:application/zip;base64,{payload}"],
                ["my-folder.zip"],
                tmpdir,
            )
            self.assertIn("confs/my-folder/POSCAR", saved)
            self.assertIn("confs/my-folder/sub/INPUT", saved)
            with open(os.path.join(tmpdir, "confs", "my-folder", "POSCAR"), "rb") as f:
                self.assertEqual(f.read(), b"POSCAR\n")

    def test_save_uploaded_files_rejects_unsafe_zip_member(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, mode="w") as zf:
            zf.writestr("../escape.txt", "bad")
        payload = base64.b64encode(stream.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                _save_uploaded_files(
                    [f"data:application/zip;base64,{payload}"],
                    ["bad.zip"],
                    tmpdir,
                )

    def test_summarize_step_progress(self):
        steps = [
            {"type": "Pod", "phase": "Pending"},
            {"type": "Pod", "phase": "Running"},
            {"type": "Pod", "phase": "Succeeded"},
            {"type": "Pod", "phase": "Skipped"},
            {"type": "StepGroup", "phase": "Running"},
        ]
        summary = _summarize_step_progress(steps)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["running"], 2)
        self.assertEqual(summary["finished"], 2)


if __name__ == "__main__":
    unittest.main()
