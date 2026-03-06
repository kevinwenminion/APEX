import json
import os
import tempfile
import unittest

from apex.gui import (
    _build_param_payload,
    _ensure_default_interaction_files,
    _extract_property_types,
    _extract_potcar_rows,
    _interaction_editor_label,
    _interaction_table_columns_for_profile,
    _interaction_table_rows_from_template,
    _interaction_type_options_for_profile,
    _load_account_state,
    _load_profile_param_template,
    _parse_extra_elements,
    _render_account_summary,
    _save_account_overwrite,
    _strip_parenthetical_suffix,
)


class TestGuiSubmitBuilder(unittest.TestCase):
    def test_build_param_payload_sets_interaction_and_req_calc(self):
        payload = _build_param_payload(
            profile="lammps",
            with_relax=False,
            selected_properties=["elastic", "eos"],
            interaction_type="eam_alloy",
            interaction_model="my_model.eam",
            element_slots=["Al", "Ni", "", ""],
        )

        self.assertNotIn("relaxation", payload)
        self.assertEqual(payload["interaction"]["type"], "eam_alloy")
        self.assertEqual(payload["interaction"]["model"], "my_model.eam")
        self.assertEqual(payload["interaction"]["type_map"], {"Al": 0, "Ni": 1})

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
            with_relax=True,
            selected_properties=[],
            interaction_type="deepmd",
            interaction_model="",
            element_slots=["", "", "", ""],
        )

        self.assertIn("relaxation", payload)
        self.assertEqual(payload["interaction"]["type"], "deepmd")
        self.assertNotIn("model", payload["interaction"])
        self.assertNotIn("type_map", payload["interaction"])

    def test_parse_extra_elements(self):
        parsed = _parse_extra_elements("Cu, Ni Fe;Cr\nMn")
        self.assertEqual(parsed, ["Cu", "Ni", "Fe", "Cr", "Mn"])

    def test_build_param_payload_dedup_elements(self):
        payload = _build_param_payload(
            profile="lammps",
            with_relax=True,
            selected_properties=[],
            interaction_type="eam_alloy",
            interaction_model="x",
            element_slots=["Al", "Ni", "Al", "Cu", "Ni"],
        )
        self.assertEqual(payload["interaction"]["type_map"], {"Al": 0, "Ni": 1, "Cu": 2})

    def test_profile_templates_have_different_property_options(self):
        lammps = _extract_property_types(_load_profile_param_template("lammps"))
        vasp = _extract_property_types(_load_profile_param_template("vasp"))
        abacus = _extract_property_types(_load_profile_param_template("abacus"))

        self.assertIn("cohesive", lammps)
        self.assertNotIn("cohesive", vasp)
        self.assertIn("phonon", vasp)
        self.assertIn("phonon", abacus)
        self.assertNotIn("phonon", lammps)

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
            with_relax=True,
            selected_properties=[],
            interaction_type="abacus",
            interaction_model="",
            element_slots=[],
            interaction_incar="abacus_input/INPUT(defaule value)",
            interaction_rows=rows,
            base_template=abacus_template,
        )
        self.assertIn("orb_files", payload["interaction"])
        self.assertIn("potcars", payload["interaction"])

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
                "incar": "abacus_input/INPUT(defaule value)",
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


if __name__ == "__main__":
    unittest.main()
