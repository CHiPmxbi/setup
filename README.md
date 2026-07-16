# CHiPmxbi Setup

Provisioning and setup tools for mxbi Raspberry Pi workstations.

This repository is intended to run from a control machine. It contains two
independent areas:

- `ansible/` manages shared workstation state across the mxbi fleet.
- `tools/` contains interactive utilities for workflows that do not fit
  declarative Ansible tasks.

## Requirements

The control machine needs Ansible and SSH access to the target Raspberry Pi. The
target account must be a non-root sudo user. Its GitHub SSH public key must
already be registered with GitHub.

```nu
brew install ansible
cd ansible
ansible-galaxy collection install -r requirements.yml
```

## Configuration

Create the inventory and encrypted Vault variables:

```nu
cp inventory/hosts.yml.example inventory/hosts.yml
cp vault/mxbi/github.yml.example vault/mxbi/github.yml
ansible-vault encrypt vault/mxbi/github.yml
ansible-vault edit vault/mxbi/github.yml
```

Edit `inventory/hosts.yml` before running the playbook. Use `ansible-vault edit`
to replace the placeholder in `vault_github_ssh_private_key`. Never write or
commit an unencrypted private key. The local `vault/mxbi/github.yml` is ignored by
Git and is loaded only by the `github` tag.

cogmoteGO email configuration is enabled during full provisioning. Set
`mxbi_cogmotego_email_address`, `mxbi_cogmotego_email_smtp_host`, and
`mxbi_cogmotego_email_smtp_port` in `roles/mxbi/defaults/main.yml`, then create
and encrypt its password Vault:

```nu
cp vault/mxbi/cogmotego_email.yml.example vault/mxbi/cogmotego_email.yml
ansible-vault encrypt vault/mxbi/cogmotego_email.yml
ansible-vault edit vault/mxbi/cogmotego_email.yml
```

Replace `vault_cogmotego_email_password` with the actual email password. This
module prepares the login keyring before storing the password and does not read
or modify cogmoteGO recipients.

The optional Samba mount module uses a separate Vault. Create and encrypt its
password file:

```nu
cp vault/mxbi/samba.yml.example vault/mxbi/samba.yml
ansible-vault encrypt vault/mxbi/samba.yml
ansible-vault edit vault/mxbi/samba.yml
```

Replace `vault_samba_password` with the real password for `anw-mxbisetup`. The
Samba Vault is loaded only when the `samba` tag is explicitly selected.

Inventory host names are OpenSSH aliases. The current `~/.ssh/config` matches
`Host mxbi*` and supplies `HostName %h.local`, user `pi`, and
`IdentityFile ~/.ssh/mxbi`, so inventory does not duplicate connection details:

```yaml
mxbi:
  hosts:
    mxbi1:
    mxbi2:
```

Verify each alias with `ssh mxbi1` before running Ansible.

## Provisioning

```nu
ansible-playbook site.yml --ask-vault-pass
```

The playbook installs system packages, HiFiBerry Amp2 configuration, Linuxbrew,
GitHub SSH credentials, Zsh configuration, cogmoteGO with email configuration,
MediaMTX, and Raspberry Pi VNC. Run the playbook again after provisioning to
confirm it is idempotent.

```nu
ansible-playbook site.yml --ask-vault-pass --check --diff
```

## Selective Runs

List available functional tags:

```nu
ansible-playbook site.yml --list-tags
```

Run one component or several components on a test host:

```nu
ansible-playbook site.yml --limit mxbi1 --tags shell
ansible-playbook site.yml --limit mxbi1 --tags 'system,homebrew'
ansible-playbook site.yml --limit mxbi1 --tags github --ask-vault-pass
ansible-playbook site.yml --limit mxbi5 --tags cogmotego_email --ask-vault-pass
ansible-playbook site.yml --limit mxbi5 --tags samba --ask-vault-pass
```

Available tags are `system`, `hifiberry`, `homebrew`, `github`, `shell`,
`cogmotego`, `cogmotego_email`, `mediamtx`, `desktop`, and `samba`.
Platform validation and user fact initialization use the `always` tag and
therefore run with every selection. `samba` also uses the special `never` tag,
so full provisioning skips it by default. Explicitly selecting `samba` loads
its Vault and mounts
`//infortrend-storage/Neurowissenschaften/AuditorischeNeurowissenschaften/Projekte/MXBI/data/<hostname>`
at `/home/pi/server`.

## Interactive Tools

`tools/` is an independent uv project for device-specific interactive setup.

```nu
cd tools
uv run setup_mxbi.py --help
uv run setup_samba_server.py --help
```

These tools are not required for Ansible provisioning.
