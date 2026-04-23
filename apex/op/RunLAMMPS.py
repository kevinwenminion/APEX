import os, subprocess, logging
from pathlib import Path
from monty.serialization import dumpfn, loadfn
from dflow.python import (
    OP,
    OPIO,
    OPIOSign,
    Artifact,
    upload_packages
)

upload_packages.append(__file__)


class RunLAMMPS(OP):
    """
    class for LAMMPS calculation
    """
    def __init__(self, infomode=1):
        self.infomode = infomode

    @classmethod
    def get_input_sign(cls):
        return OPIOSign({
            'input_lammps': Artifact(Path),
            'run_command': str
        })

    @classmethod
    def get_output_sign(cls):
        return OPIOSign({
            'backward_dir': Artifact(Path, sub_path=False)
        })

    @classmethod
    def _cleanup_model_links(cls, task_dir):
        task_path = Path(task_dir)
        inter_json = task_path / "inter.json"
        if not inter_json.exists():
            return

        try:
            inter_param = loadfn(inter_json)
        except Exception as exc:
            logging.warning(f"Failed to load inter.json for symlink cleanup: {exc}")
            return

        model_spec = inter_param.get("model", [])
        if isinstance(model_spec, str):
            model_list = [model_spec]
        elif isinstance(model_spec, list):
            model_list = model_spec
        else:
            model_list = []

        for model in model_list:
            link_candidates = {task_path / model, task_path / Path(model).name}
            for link_path in link_candidates:
                if link_path.is_symlink() and not link_path.exists():
                    link_path.unlink()

    @OP.exec_sign_check
    def execute(self, op_in: OPIO) -> OPIO:
        cwd = os.getcwd()
        task_dir = Path(op_in["input_lammps"])
        marker_file = task_dir / "apex_lammps_failed.json"

        try:
            os.chdir(task_dir)
            if os.path.exists("run_command"):
                with open("run_command", 'r') as f:
                    cmd = f.read()
            else:
                cmd = op_in["run_command"]

            exit_code = subprocess.call(cmd, shell=True)
            if exit_code == 0:
                logging.info("Call Lammps command successfully!")
                if marker_file.exists():
                    marker_file.unlink()
            else:
                logging.warning(f"Call Lammps command failed with exit code: {exit_code}")
                dumpfn(
                    {
                        "exit_code": int(exit_code),
                        "run_command": cmd,
                    },
                    marker_file,
                    indent=4,
                )

            self._cleanup_model_links(task_dir)
        finally:
            os.chdir(cwd)

        op_out = OPIO({
            "backward_dir": op_in["input_lammps"]
        })
        return op_out
