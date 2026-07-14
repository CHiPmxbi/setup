#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "cyclopts>=4.21.0",
# ]
# ///
"""配置 Samba/CIFS systemd .mount 单元的 CLI 和 Python API。"""

import getpass
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from cyclopts import App


@dataclass(frozen=True, slots=True)
class Messages:
    app_help: str
    setup_help: str
    default_help: str
    share: str
    mount_path: str
    domain: str
    username: str
    password: str
    generated_unit: str
    path: str
    credential: str
    encryption: str
    confirm_write: str
    cancelled: str
    enable_now: str
    completed: str
    status: str
    error: str


EN_MESSAGES: Final = Messages(
    app_help="Interactively create Samba/CIFS systemd .mount units.",
    setup_help="Create a Samba/CIFS .mount unit.",
    default_help="Start interactive setup by default.",
    share="Samba share, for example //192.168.1.10/share",
    mount_path="Local mount path",
    domain="Domain/workgroup; leave empty when unused",
    username="Samba username",
    password="Samba password",
    generated_unit="The following .mount unit will be generated:",
    path="Path: {path}",
    credential="Encrypted credential: {path}",
    encryption="Encryption: systemd-creds --with-key=host",
    confirm_write="Create the encrypted credential and write these files",
    cancelled="Cancelled.",
    enable_now="Enable and start {unit} now",
    completed="Completed.",
    status="Check status: systemctl status {unit}",
    error="Error: {error}",
)


ZH_MESSAGES: Final = Messages(
    app_help="交互式创建 Samba/CIFS systemd .mount 单元。",
    setup_help="创建 Samba/CIFS .mount 单元。",
    default_help="默认进入交互式配置。",
    share="Samba 共享地址，例如 //192.168.1.10/share",
    mount_path="本地挂载路径",
    domain="Domain/Workgroup，可留空",
    username="Samba 用户名",
    password="Samba 密码",
    generated_unit="将生成以下 .mount 单元：",
    path="路径：{path}",
    credential="加密 credential：{path}",
    encryption="加密方式：systemd-creds --with-key=host",
    confirm_write="确认写入并创建加密 credential",
    cancelled="已取消。",
    enable_now="是否 enable --now {unit}",
    completed="完成。",
    status="查看状态：systemctl status {unit}",
    error="错误：{error}",
)


def detect_language() -> Literal["en", "zh"]:
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value:
            return "zh" if value.lower().startswith("zh") else "en"
    return "en"


LANGUAGE: Final = detect_language()
MESSAGES: Final = ZH_MESSAGES if LANGUAGE == "zh" else EN_MESSAGES


class SambaMountError(RuntimeError):
    """Samba 挂载配置失败。"""


@dataclass(frozen=True, slots=True)
class SambaMountConfig:
    """用户提供的 Samba 挂载配置。"""

    server: str
    mount_path: str
    domain: str
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class SambaMountResult:
    """解析或安装 Samba 挂载后的结果。"""

    unit_name: str
    unit_path: Path
    credential_path: Path
    unit_content: str


def _run(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise SambaMountError(f"Required command is missing: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or "command failed"
        raise SambaMountError(f"{' '.join(command[:2])}: {message}") from exc


def _sudo_command(*args: str) -> list[str]:
    return list(args) if os.geteuid() == 0 else ["sudo", *args]


def _validate_config(config: SambaMountConfig) -> None:
    server_parts = config.server.split("/")
    if (
        not config.server.startswith("//")
        or len(server_parts) < 4
        or not server_parts[2]
        or not server_parts[3]
    ):
        raise SambaMountError("Samba share must use the //server/share format")
    if not Path(config.mount_path).is_absolute():
        raise SambaMountError("Mount path must be absolute")
    if not config.username:
        raise SambaMountError("Samba username must not be empty")
    if not config.password:
        raise SambaMountError("Samba password must not be empty")
    for value in (config.server, config.mount_path, config.domain, config.username, config.password):
        if "\n" in value or "\r" in value:
            raise SambaMountError("Samba configuration values must not contain newlines")


def _original_user_ids() -> tuple[str, str]:
    uid = os.environ.get("SUDO_UID")
    gid = os.environ.get("SUDO_GID")
    if uid and gid and uid.isdecimal() and gid.isdecimal():
        return uid, gid
    return str(os.getuid()), str(os.getgid())


def _unit_name(mount_path: str) -> str:
    return _run(["systemd-escape", "--path", "--suffix=mount", mount_path]).stdout.strip()


def _credential_content(config: SambaMountConfig) -> str:
    lines = [f"username={config.username}", f"password={config.password}"]
    if config.domain:
        lines.append(f"domain={config.domain}")
    return "\n".join(lines) + "\n"


def render_samba_mount(config: SambaMountConfig) -> SambaMountResult:
    """生成 Samba .mount unit 内容，不修改系统。"""

    _validate_config(config)
    unit_name = _unit_name(config.mount_path)
    uid, gid = _original_user_ids()
    unit_path = Path("/etc/systemd/system") / unit_name
    credential_path = Path("/etc/credstore.encrypted") / f"{unit_name.removesuffix('.mount')}.cred"
    options = ",".join(
        (
            "credentials=%d/cifs-credentials",
            f"uid={uid}",
            f"gid={gid}",
            "vers=3.1.1",
            "_netdev",
            "rw",
        )
    )
    unit_content = f"""[Unit]
Description=Mount Samba Share ({config.server})
After=network-online.target
Wants=network-online.target

[Mount]
What={config.server}
Where={config.mount_path}
Type=cifs
Options={options}
LoadCredentialEncrypted=cifs-credentials:{credential_path}
TimeoutSec=30s

[Install]
WantedBy=multi-user.target
"""
    return SambaMountResult(unit_name, unit_path, credential_path, unit_content)


def _ensure_sudo_ready() -> None:
    if os.geteuid() != 0:
        _run(["sudo", "-v"])


def _write_credential(config: SambaMountConfig, result: SambaMountResult) -> None:
    _run(_sudo_command("mkdir", "-p", str(result.credential_path.parent)))
    _run(
        _sudo_command(
            "systemd-creds",
            "encrypt",
            "--with-key=host",
            "--name=cifs-credentials",
            "-",
            str(result.credential_path),
        ),
        input_text=_credential_content(config),
    )
    _run(_sudo_command("chmod", "0600", str(result.credential_path)))


def _write_unit(result: SambaMountResult) -> None:
    _run(
        _sudo_command("install", "-m", "0644", "/dev/stdin", str(result.unit_path)),
        input_text=result.unit_content,
    )


def install_samba_mount(config: SambaMountConfig, *, enable_now: bool = False) -> SambaMountResult:
    """安装 Samba credential 和 .mount unit，并重载 systemd。"""

    _validate_config(config)
    result = render_samba_mount(config)
    _ensure_sudo_ready()
    _write_credential(config, result)
    _write_unit(result)
    _run(_sudo_command("systemctl", "daemon-reload"))
    if enable_now:
        _run(_sudo_command("systemctl", "enable", "--now", result.unit_name))
    return result


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while not (value := input(f"{prompt}{suffix}: ").strip()):
        if default is not None:
            return default
    return value


def _ask_bool(prompt: str, default: bool = False) -> bool:
    default_text = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "true", "1", "是"}


def run_interactive_setup(*, dry_run: bool = False, enable_now: bool = False) -> SambaMountResult | None:
    """交互收集 Samba 配置并生成或安装 .mount unit。"""

    server = _ask(MESSAGES.share)
    mount_path = _ask(MESSAGES.mount_path, "/mnt/samba")
    domain = _ask(MESSAGES.domain, "")
    username = _ask(MESSAGES.username)
    password = getpass.getpass(f"{MESSAGES.password}: ")
    config = SambaMountConfig(server, mount_path, domain, username, password)
    result = render_samba_mount(config)

    print(f"\n{MESSAGES.generated_unit}")
    print(f"{MESSAGES.path.format(path=result.unit_path)}\n")
    print(result.unit_content)
    print(MESSAGES.credential.format(path=result.credential_path))
    print(MESSAGES.encryption)

    if dry_run:
        return result
    if not _ask_bool(MESSAGES.confirm_write, True):
        print(MESSAGES.cancelled)
        return None
    if enable_now or _ask_bool(MESSAGES.enable_now.format(unit=result.unit_name), False):
        enable_now = True
    result = install_samba_mount(config, enable_now=enable_now)
    print(f"\n{MESSAGES.completed}")
    print(MESSAGES.status.format(unit=result.unit_name))
    return result


def create_cli_app() -> "App":
    """创建独立运行 setup_samba_server.py 时使用的 Cyclopts app。"""

    from cyclopts import App

    app = App(help=MESSAGES.app_help)

    @app.command
    def setup(*, dry_run: bool = False, enable_now: bool = False) -> None:
        """Create a Samba/CIFS .mount unit."""
        run_interactive_setup(dry_run=dry_run, enable_now=enable_now)

    @app.default
    def default(*, dry_run: bool = False, enable_now: bool = False) -> None:
        """Start interactive setup by default."""
        run_interactive_setup(dry_run=dry_run, enable_now=enable_now)

    setup.__doc__ = MESSAGES.setup_help
    default.__doc__ = MESSAGES.default_help
    return app


def main() -> None:
    try:
        create_cli_app()()
    except SambaMountError as exc:
        print(MESSAGES.error.format(error=exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
