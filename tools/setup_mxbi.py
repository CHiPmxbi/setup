#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "cyclopts>=4.21.0",
# ]
# ///
"""mxbi 系统配置的统一 CLI 入口。"""

import os
import sys
from typing import Final

from cyclopts import App

from setup_samba_server import SambaMountError, run_interactive_setup


MESSAGES: Final = {
    "en": {
        "app_help": "mxbi system setup tools.",
        "samba_help": "Interactively configure a Samba/CIFS mount.",
        "error": "Error: {error}",
    },
    "zh": {
        "app_help": "mxbi 系统配置工具。",
        "samba_help": "交互式配置 Samba/CIFS 挂载。",
        "error": "错误：{error}",
    },
}


def _detect_language() -> str:
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value:
            return "zh" if value.lower().startswith("zh") else "en"
    return "en"


LANGUAGE: Final = _detect_language()


def _tr(key: str, **kwargs: object) -> str:
    return MESSAGES[LANGUAGE][key].format(**kwargs)


def create_cli_app() -> App:
    """创建 mxbi 的综合 CLI。"""

    app = App(help=_tr("app_help"))

    @app.command
    def samba(*, dry_run: bool = False, enable_now: bool = False) -> None:
        """Interactively configure a Samba/CIFS mount."""
        run_interactive_setup(dry_run=dry_run, enable_now=enable_now)

    samba.__doc__ = _tr("samba_help")
    return app


def main() -> None:
    try:
        create_cli_app()()
    except SambaMountError as exc:
        print(_tr("error", error=exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
