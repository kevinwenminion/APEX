import json
import logging
import os
import re
import shutil
from typing import Dict, List, Optional

from apex.submit import submit_from_args


TASK_DIR_PATTERN = re.compile(r"^task\.\d+$")


def _detect_engine(task_dir: str) -> str:
    files = set(os.listdir(task_dir))
    if "in.lammps" in files or "conf.lmp" in files:
        return "lammps"
    if "INCAR" in files:
        return "vasp"
    if "INPUT" in files and "STRU" in files:
        return "abacus"
    return "unknown"


def discover_retryable_tasks(failed_root: str) -> List[str]:
    found = []
    if not os.path.isdir(failed_root):
        return found

    for current_root, dirs, _files in os.walk(failed_root):
        for dirname in list(dirs):
            if not TASK_DIR_PATTERN.match(dirname):
                continue
            candidate = os.path.join(current_root, dirname)
            if os.path.isdir(candidate):
                found.append(os.path.abspath(candidate))

    # Keep deterministic ordering for reproducible manifests.
    found = sorted(set(found))
    return found


def _safe_name_from_relpath(rel_path: str, index: int) -> str:
    token = rel_path.replace(os.sep, "__")
    token = re.sub(r"[^a-zA-Z0-9_.-]", "-", token)
    return f"task_{index:04d}__{token}"


def build_retry_workspace(
        failed_root: str,
        output_dir: str,
        manifest_path: Optional[str] = None,
) -> Dict[str, object]:
    failed_root = os.path.abspath(failed_root)
    output_dir = os.path.abspath(output_dir)
    tasks = discover_retryable_tasks(failed_root)

    os.makedirs(output_dir, exist_ok=True)
    staged_root = os.path.join(output_dir, "failed_tasks")
    os.makedirs(staged_root, exist_ok=True)

    manifest_tasks: List[Dict[str, str]] = []
    for index, src in enumerate(tasks, start=1):
        rel = os.path.relpath(src, failed_root)
        staged_name = _safe_name_from_relpath(rel, index)
        dst = os.path.join(staged_root, staged_name)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        manifest_tasks.append(
            {
                "source": src,
                "relative_from_failed_root": rel,
                "staged": dst,
                "engine": _detect_engine(src),
            }
        )

    engine_stats: Dict[str, int] = {}
    for item in manifest_tasks:
        engine = item["engine"]
        engine_stats[engine] = engine_stats.get(engine, 0) + 1

    result: Dict[str, object] = {
        "failed_root": failed_root,
        "output_dir": output_dir,
        "staged_root": staged_root,
        "task_count": len(manifest_tasks),
        "engine_stats": engine_stats,
        "tasks": manifest_tasks,
    }

    if manifest_path is None:
        manifest_path = os.path.join(output_dir, "retry_manifest.json")
    manifest_path = os.path.abspath(manifest_path)
    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2)
    result["manifest_path"] = manifest_path

    checklist_path = os.path.join(output_dir, "retry_submit_checklist.json")
    checklist = {
        "workspace": output_dir,
        "failed_root": failed_root,
        "staged_root": staged_root,
        "task_count": len(manifest_tasks),
        "next_step": [
            "Prepare param_*.json and global*.json for this workspace",
            "Run apex submit <param.json> -w <workspace> -c <global.json>",
            "Or use apex replay-failed --submit with these files",
        ],
    }
    with open(checklist_path, "w", encoding="utf-8") as fp:
        json.dump(checklist, fp, indent=2)
    result["checklist_path"] = os.path.abspath(checklist_path)

    return result


def replay_failed_from_args(args):
    failed_root = os.path.join(args.work, args.failed_root)
    result = build_retry_workspace(
        failed_root=failed_root,
        output_dir=args.output,
        manifest_path=args.manifest,
    )

    print(f"Found {result['task_count']} retryable task directories")
    print(f"Retry workspace: {result['output_dir']}")
    print(f"Manifest: {result['manifest_path']}")
    print(f"Checklist: {result['checklist_path']}")

    if args.submit:
        if not args.parameter:
            raise RuntimeError("--submit requires at least one parameter json via --parameter")
        if result["task_count"] == 0:
            raise RuntimeError("No retryable tasks found. Skip auto-submit.")

        logging.info("Auto-submit retry workspace via apex submit")
        submit_from_args(
            parameters=args.parameter,
            config_file=args.config,
            work_dirs=[result["output_dir"]],
            indicated_flow_type=args.flow,
            flow_name=args.name,
            submit_only=args.submit_only,
            is_debug=args.debug,
        )

    return result
