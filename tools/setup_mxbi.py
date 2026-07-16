#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "cyclopts>=4.21.0",
# ]
# ///
"""mxbi 系统配置的统一 CLI 入口。"""

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Final

from cyclopts import App

from setup_samba_server import SambaMountError, run_interactive_setup


CONFIG_REPOSITORY: Final = "git@github.com:CHiPmxbi/mxbi_share_config.git"
EXPERIMENT_ORGANIZATION: Final = "git@github.com:CHiPmxbi"

MESSAGES: Final = {
    "en": {
        "app_help": "Interactively set up an mxbi workstation.",
        "default_help": "Run the complete mxbi setup.",
        "step_config": "[1/4] Clone shared configuration",
        "step_experiment": "[2/4] Clone an experiment",
        "step_samba": "[3/4] Configure the Samba mount",
        "step_cogmotego": "[4/4] Configure cogmoteGO trusted roots",
        "experiment": "Experiment repository name (must start with exp-)",
        "experiment_prefix": "Experiment repository name must start with exp-",
        "exists": "Target already exists: {path}",
        "config_exists": "Shared configuration already exists; skipping: {path}",
        "cancelled": "Samba setup was cancelled; stopping setup.",
        "dry_run": "Would run: {command}",
        "completed": "mxbi setup completed.",
        "error": "Error: {error}",
    },
    "zh": {
        "app_help": "交互式配置 mxbi 工作站。",
        "default_help": "执行完整的 mxbi 配置流程。",
        "step_config": "[1/4] 克隆共享配置",
        "step_experiment": "[2/4] 克隆实验",
        "step_samba": "[3/4] 配置 Samba 挂载",
        "step_cogmotego": "[4/4] 配置 cogmoteGO 可信目录",
        "experiment": "实验仓库名称（必须以 exp- 开头）",
        "experiment_prefix": "实验仓库名称必须以 exp- 开头",
        "exists": "目标已存在：{path}",
        "config_exists": "共享配置已存在，跳过：{path}",
        "cancelled": "Samba 配置已取消，停止后续流程。",
        "dry_run": "将执行：{command}",
        "completed": "mxbi 配置完成。",
        "error": "错误：{error}",
    },
}


class SetupError(RuntimeError):
    """mxbi 配置失败。"""


def _detect_language() -> str:
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value:
            return "zh" if value.lower().startswith("zh") else "en"
    return "en"


LANGUAGE: Final = _detect_language()


def _tr(key: str, **kwargs: object) -> str:
    return MESSAGES[LANGUAGE][key].format(**kwargs)


def _run(command: list[str], *, dry_run: bool = False) -> None:
    if dry_run:
        print(_tr("dry_run", command=shlex.join(command)))
        return
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SetupError(f"Required command is missing: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SetupError(f"Command failed ({exc.returncode}): {shlex.join(command)}") from exc


def _clone(repository: str, destination: Path, *, dry_run: bool) -> None:
    if destination.exists():
        raise SetupError(_tr("exists", path=destination))
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "clone", repository, str(destination)], dry_run=dry_run)


def _ask_experiment() -> str:
    while True:
        name = input(f"{_tr('experiment')}: ").strip()
        if name.startswith("exp-") and name != "exp-" and "/" not in name:
            return name
        print(_tr("experiment_prefix"), file=sys.stderr)


def run_setup(*, dry_run: bool = False) -> None:
    """按顺序执行 mxbi 的完整配置流程。"""

    home = Path.home()
    config_path = home / ".config" / "mxbi"

    print(_tr("step_config"))
    if config_path.exists():
        print(_tr("config_exists", path=config_path))
    else:
        _clone(CONFIG_REPOSITORY, config_path, dry_run=dry_run)

    print(f"\n{_tr('step_experiment')}")
    experiment = _ask_experiment()
    experiment_path = home / experiment
    samba_path = experiment_path / "server"
    data_path = experiment_path / "data"
    _clone(
        f"{EXPERIMENT_ORGANIZATION}/{experiment}.git",
        experiment_path,
        dry_run=dry_run,
    )

    print(f"\n{_tr('step_samba')}")
    samba_result = run_interactive_setup(
        dry_run=dry_run,
        enable_now=True,
        mount_path=samba_path,
    )
    if samba_result is None:
        raise SetupError(_tr("cancelled"))

    print(f"\n{_tr('step_cogmotego')}")
    if not dry_run:
        data_path.mkdir(parents=True, exist_ok=True)
    _run(
        ["cogmoteGO", "backup", "roots", "add", "samba", "mxbi-server", str(samba_path)],
        dry_run=dry_run,
    )
    _run(
        ["cogmoteGO", "backup", "roots", "add", "source", "mxbi-data", str(data_path)],
        dry_run=dry_run,
    )
    _run(["cogmoteGO", "service", "restart", "-u"], dry_run=dry_run)
    print(f"\n{_tr('completed')}")


def create_cli_app() -> App:
    """创建 mxbi 的综合 CLI。"""

    app = App(help=_tr("app_help"))

    @app.default
    def default(*, dry_run: bool = False) -> None:
        """Run the complete mxbi setup."""

        run_setup(dry_run=dry_run)

    default.__doc__ = _tr("default_help")
    return app


def main() -> None:
    try:
        create_cli_app()()
    except (SetupError, SambaMountError) as exc:
        print(_tr("error", error=exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
