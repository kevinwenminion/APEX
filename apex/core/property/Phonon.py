import glob
import json
import logging
import os
import shutil
import re
import subprocess

import dpdata

from ..calculator.lib import abacus_utils
from ..calculator.lib import vasp_utils
from .Property import Property
from ..refine import make_refine
from ..reproduce import make_repro, post_repro
from dflow.python import upload_packages
upload_packages.append(__file__)


class Phonon(Property):
    def __init__(self, parameter, inter_param=None):
        parameter["reproduce"] = parameter.get("reproduce", False)
        self.reprod = parameter["reproduce"]
        if not self.reprod:
            if not ("init_from_suffix" in parameter and "output_suffix" in parameter):
                self.primitive = parameter.get('primitive', False)
                self.approach = parameter.get('approach', 'linear')
                self.band_path = parameter.get('band_path')
                self.supercell_size = parameter.get('supercell_size', [2, 2, 2])
                self.primitive = parameter.get('primitive')
                self.MESH = parameter.get('MESH', None)
                self.PRIMITIVE_AXES = parameter.get('PRIMITIVE_AXES', None)
                self.BAND_POINTS = parameter.get('BAND_POINTS', None)
                self.BAND_CONNECTION = parameter.get('BAND_CONNECTION', True)
            parameter["cal_type"] = parameter.get("cal_type", "relaxation")
            self.cal_type = parameter["cal_type"]
            default_cal_setting = {
                "relax_pos": True,
                "relax_shape": True,
                "relax_vol": False,
            }
            if "cal_setting" not in parameter:
                parameter["cal_setting"] = default_cal_setting
            else:
                if "relax_pos" not in parameter["cal_setting"]:
                    parameter["cal_setting"]["relax_pos"] = default_cal_setting[
                        "relax_pos"
                    ]
                if "relax_shape" not in parameter["cal_setting"]:
                    parameter["cal_setting"]["relax_shape"] = default_cal_setting[
                        "relax_shape"
                    ]
                if "relax_vol" not in parameter["cal_setting"]:
                    parameter["cal_setting"]["relax_vol"] = default_cal_setting[
                        "relax_vol"
                    ]
            self.cal_setting = parameter["cal_setting"]
        else:
            parameter["cal_type"] = "static"
            self.cal_type = parameter["cal_type"]
            default_cal_setting = {
                "relax_pos": False,
                "relax_shape": False,
                "relax_vol": False,
            }
            if "cal_setting" not in parameter:
                parameter["cal_setting"] = default_cal_setting
            else:
                if "relax_pos" not in parameter["cal_setting"]:
                    parameter["cal_setting"]["relax_pos"] = default_cal_setting[
                        "relax_pos"
                    ]
                if "relax_shape" not in parameter["cal_setting"]:
                    parameter["cal_setting"]["relax_shape"] = default_cal_setting[
                        "relax_shape"
                    ]
                if "relax_vol" not in parameter["cal_setting"]:
                    parameter["cal_setting"]["relax_vol"] = default_cal_setting[
                        "relax_vol"
                    ]
            self.cal_setting = parameter["cal_setting"]
            parameter["init_from_suffix"] = parameter.get("init_from_suffix", "00")
            self.init_from_suffix = parameter["init_from_suffix"]
        self.parameter = parameter
        self.inter_param = inter_param if inter_param is not None else {"type": "vasp"}

    def make_confs(self, path_to_work, path_to_equi, refine=False):
        path_to_work = os.path.abspath(path_to_work)
        if os.path.exists(path_to_work):
            #dlog.warning("%s already exists" % path_to_work)
            logging.warning("%s already exists" % path_to_work)
        else:
            os.makedirs(path_to_work)
        path_to_equi = os.path.abspath(path_to_equi)

        if "start_confs_path" in self.parameter and os.path.exists(
            self.parameter["start_confs_path"]
        ):
            init_path_list = glob.glob(
                os.path.join(self.parameter["start_confs_path"], "*")
            )
            struct_init_name_list = []
            for ii in init_path_list:
                struct_init_name_list.append(ii.split("/")[-1])
            struct_output_name = path_to_work.split("/")[-2]
            assert struct_output_name in struct_init_name_list
            path_to_equi = os.path.abspath(
                os.path.join(
                    self.parameter["start_confs_path"],
                    struct_output_name,
                    "relaxation",
                    "relax_task",
                )
            )

        task_list = []
        cwd = os.getcwd()

        if self.reprod:
            print("phonon reproduce starts")
            if "init_data_path" not in self.parameter:
                raise RuntimeError("please provide the initial data path to reproduce")
            init_data_path = os.path.abspath(self.parameter["init_data_path"])
            task_list = make_repro(
                self.inter_param,
                init_data_path,
                self.init_from_suffix,
                path_to_work,
                self.parameter.get("reprod_last_frame", True),
            )
            os.chdir(cwd)

        else:
            if refine:
                print("phonon refine starts")
                task_list = make_refine(
                    self.parameter["init_from_suffix"],
                    self.parameter["output_suffix"],
                    path_to_work,
                )
                os.chdir(cwd)

            else:
                if self.inter_param["type"] == "abacus":
                    CONTCAR = abacus_utils.final_stru(path_to_equi)
                    POSCAR = "STRU"
                else:
                    CONTCAR = "CONTCAR"
                    POSCAR = "POSCAR"

                equi_contcar = os.path.join(path_to_equi, CONTCAR)
                if not os.path.exists(equi_contcar):
                    raise RuntimeError("please do relaxation first")

                if self.inter_param["type"] == "abacus":
                    stru = dpdata.System(equi_contcar, fmt="stru")
                    stru.to("contcar", "CONTCAR.tmp")
                    ptypes = vasp_utils.get_poscar_types("CONTCAR.tmp")
                    os.remove("CONTCAR.tmp")
                else:
                    ptypes = vasp_utils.get_poscar_types(equi_contcar)
                    # gen structure

                os.chdir(path_to_work)
                if os.path.isfile(POSCAR):
                    os.remove(POSCAR)
                if os.path.islink(POSCAR):
                    os.remove(POSCAR)
                os.symlink(os.path.relpath(equi_contcar), POSCAR)
                #           task_poscar = os.path.join(output, 'POSCAR')

                # prepare band.conf
                ret = ""
                ret += "ATOM_NAME ="
                for ii in ptypes:
                    ret += " %s" % ii
                ret += "\n"
                ret += "DIM = %s %s %s\n" % (
                    self.supercell_size[0],
                    self.supercell_size[1],
                    self.supercell_size[2]
                )
                if self.MESH:
                    ret += "MESH = %s %s %s\n" % (
                        self.MESH[0], self.MESH[1], self.MESH[2]
                    )
                if self.PRIMITIVE_AXES:
                    ret += "PRIMITIVE_AXES = %s\n" % self.PRIMITIVE_AXES
                ret += "BAND = %s\n" % self.band_path
                if self.BAND_POINTS:
                    ret += "BAND_POINTS = %s\n" % self.BAND_POINTS
                if self.BAND_CONNECTION:
                    ret += "BAND_CONNECTION = %s\n" % self.BAND_CONNECTION

                ret_force_read = ret + "FORCE_CONSTANTS=READ\n"

                task_list = []
                # ------------make for abacus---------------
                if self.inter_param["type"] == "abacus":
                    ret_sc = ""
                    ret_sc += "DIM=%s %s %s\n" % (
                        self.supercell_size[0],
                        self.supercell_size[1],
                        self.supercell_size[2]
                    )
                    ret_sc += "ATOM_NAME ="
                    for atom in ptypes:
                        ret += " %s" % (atom)
                    ret_sc += "\n"
                    with open("setting.conf", "a") as fp:
                        fp.write(ret_sc)
                    ## generate STRU-00x
                    cmd = "phonopy setting.conf --abacus -d"
                    subprocess.call(cmd, shell=True)

                    with open("band.conf", "a") as fp:
                        fp.write(ret)
                    # generate task.000*
                    stru_list = glob.glob("STRU-0*")
                    for ii in range(len(stru_list)):
                        task_path = os.path.join(path_to_work, 'task.%06d' % ii)
                        os.makedirs(task_path, exist_ok=True)
                        os.chdir(task_path)
                        task_list.append(task_path)
                        os.symlink(os.path.join(path_to_work, stru_list[ii]), 'STRU')
                        os.symlink(os.path.join(path_to_work, 'STRU'), 'STRU.ori')
                        os.symlink(os.path.join(path_to_work, 'band.conf'), 'band.conf')
                        os.symlink(os.path.join(path_to_work, 'phonopy_disp.yaml'), 'phonopy_disp.yaml')
                        try:
                            os.symlink(os.path.join(path_to_work, 'KPT'), 'KPT')
                        except:
                            pass
                    os.chdir(cwd)
                    return task_list

                # ------------make for vasp and lammps------------
                if self.primitive:
                    subprocess.call('phonopy --symmetry', shell=True)
                    subprocess.call('cp PPOSCAR POSCAR', shell=True)
                    shutil.copyfile("PPOSCAR", "POSCAR-unitcell")
                else:
                    shutil.copyfile("POSCAR", "POSCAR-unitcell")

                # make tasks
                if self.inter_param["type"] == 'vasp':
                    cmd = "phonopy -d --dim='%d %d %d' -c POSCAR" % (
                        int(self.supercell_size[0]),
                        int(self.supercell_size[1]),
                        int(self.supercell_size[2])
                    )
                    subprocess.call(cmd, shell=True)
                    # linear response method
                    if self.approach == 'linear':
                        task_path = os.path.join(path_to_work, 'task.000000')
                        os.makedirs(task_path, exist_ok=True)
                        os.chdir(task_path)
                        task_list.append(task_path)
                        os.symlink(os.path.join(path_to_work, "SPOSCAR"), "POSCAR")
                        os.symlink(os.path.join(path_to_work, "POSCAR-unitcell"), "POSCAR-unitcell")
                        with open("band.conf", "a") as fp:
                            fp.write(ret_force_read)
                    # finite displacement method
                    elif self.approach == 'displacement':
                        poscar_list = glob.glob("POSCAR-0*")
                        for ii in range(len(poscar_list)):
                            task_path = os.path.join(path_to_work, 'task.%06d' % ii)
                            os.makedirs(task_path, exist_ok=True)
                            os.chdir(task_path)
                            task_list.append(task_path)
                            os.symlink(os.path.join(path_to_work, poscar_list[ii]), 'POSCAR')
                            os.symlink(os.path.join(path_to_work, "POSCAR-unitcell"), "POSCAR-unitcell")

                        os.chdir(path_to_work)
                        with open("band.conf", "a") as fp:
                            fp.write(ret)
                        shutil.copyfile("band.conf", "task.000000/band.conf")
                        shutil.copyfile("phonopy_disp.yaml", "task.000000/phonopy_disp.yaml")

                    else:
                        raise RuntimeError(
                            f'Unsupported phonon approach input: {self.approach}. '
                            f'Please choose from "linear" and "displacement".'
                        )
                    os.chdir(cwd)
                    return task_list
                # ----------make for lammps-------------
                elif self.inter_param["type"] in ["deepmd", "meam", "eam_fs", "eam_alloy"]:
                    task_path = os.path.join(path_to_work, 'task.000000')
                    os.makedirs(task_path, exist_ok=True)
                    os.chdir(task_path)
                    task_list.append(task_path)
                    os.symlink(os.path.join(path_to_work, "POSCAR-unitcell"), POSCAR)
                    #vasp.regulate_poscar("POSCAR", "POSCAR")
                    #vasp.sort_poscar("POSCAR", "POSCAR", ptypes)

                    with open("band.conf", "a") as fp:
                        fp.write(ret_force_read)
                    os.chdir(cwd)
                    return task_list
                else:
                    raise RuntimeError(
                        f'Unsupported interaction type input: {self.inter_param["type"]}'
                    )

    def post_process(self, task_list):
        cwd = os.getcwd()
        inter_type = self.inter_param["type"]
        if inter_type in ["deepmd", "meam", "eam_fs", "eam_alloy"]:
            # prepare in.lammps
            for ii in task_list:
                os.chdir(ii)
                with open("in.lammps", 'r') as f1:
                    contents = f1.readlines()
                    for jj in range(len(contents)):
                        is_pair_coeff = re.search("pair_coeff", contents[jj])
                        if is_pair_coeff:
                            pair_line_id = jj
                            break
                    del contents[pair_line_id + 1:]

                with open("in.lammps", 'w') as f2:
                    for jj in range(len(contents)):
                        f2.write(contents[jj])
                # dump phonolammps command
                phonolammps_cmd = "phonolammps in.lammps -c POSCAR --dim %s %s %s " %(
                    self.supercell_size[0], self.supercell_size[1], self.supercell_size[2]
                )
                with open("run_command", 'w') as f3:
                    f3.write(phonolammps_cmd)
        elif inter_type == "vasp":
            pass
        elif inter_type == "abacus":
            pass
        os.chdir(cwd)

    def task_type(self):
        return self.parameter["type"]

    def task_param(self):
        return self.parameter

    def _compute_lower(self, output_file, all_tasks, all_res):
        cwd = os.getcwd()
        output_file = os.path.abspath(output_file)
        res_data = {}
        ptr_data = os.path.dirname(output_file) + "\n"

        if not self.reprod:
            if self.inter_param["type"] == 'abacus':
                pass
            elif self.inter_param["type"] == 'vasp':
                pass
            elif self.inter_param["type"] in ["deepmd", "meam", "eam_fs", "eam_alloy"]:
                os.chdir(all_tasks[0])
                if not os.path.exists('FORCE_CONSTANTS'):
                    raise RuntimeError('"FORCE_CONSTANTS" file not found!')
                os.system('phonopy --dim="%s %s %s" -c POSCAR band.conf' % (
                    self.supercell_size[0], self.supercell_size[1], self.supercell_size[2])
                    )
                os.system('phonopy-bandplot --gnuplot band.yaml > band.dat')
                shutil.copyfile("band.dat", os.path.join(cwd, "band.dat"))

        else:
            if "init_data_path" not in self.parameter:
                raise RuntimeError("please provide the initial data path to reproduce")
            init_data_path = os.path.abspath(self.parameter["init_data_path"])
            res_data, ptr_data = post_repro(
                init_data_path,
                self.parameter["init_from_suffix"],
                all_tasks,
                ptr_data,
                self.parameter.get("reprod_last_frame", True),
            )

        os.chdir(cwd)
        print(os.getcwd())
        print(os.listdir(cwd))
        with open('band.dat', 'r') as f:
            ptr_data = f.read()

        result_points = ptr_data.split('\n')[1]
        result_lines = ptr_data.split('\n')[2:]
        res_data[result_points] = result_lines

        with open(output_file, "w") as fp:
            json.dump(res_data, fp, indent=4)

        return res_data, ptr_data