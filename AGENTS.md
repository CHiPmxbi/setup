# Repository Notes

- Treat `ansible/site.yml` as the provisioning entrypoint.
- The repository is a control-machine setup project and must not be cloned onto managed devices as part of provisioning.

## Python Tools

- `tools/` is an independent uv project pinned to Python 3.14 by `.python-version`, `pyproject.toml`, and `uv.lock`. Enter `tools/` first, then run scripts directly with `uv run setup_mxbi.py ...` or `uv run setup_samba_server.py ...`.
- Focused verification from `tools/` is `uv run python -m py_compile setup_samba_server.py setup_mxbi.py`.
- `tools/setup_samba_server.py` is both a standalone Cyclopts CLI and a Python API. Preserve its public `SambaMountConfig`, `SambaMountResult`, `render_samba_mount()`, `install_samba_mount()`, and `run_interactive_setup()` interfaces.
- `tools/setup_mxbi.py` is the top-level interactive workflow. It calls `setup_samba_server.py` directly rather than spawning it as a subprocess.
- Samba installation is Linux/systemd-specific and privileged: it invokes `systemd-escape`, `systemd-creds`, and `systemctl`, writes `/etc/credstore.encrypted/` and `/etc/systemd/system/`, and prompts for `sudo`. Use `--dry-run` for non-writing verification.
