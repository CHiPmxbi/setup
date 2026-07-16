# CHiPmxbi Setup

Provisioning and setup tools for mxbi Raspberry Pi workstations.

This repository is intended to run from a control machine. Its top-level
Ansible playbooks manage shared workstation state and experiment deployment.

## Requirements

The control machine needs Ansible and SSH access to the target Raspberry Pi. The
target account must be a non-root sudo user. Its GitHub SSH public key must
already be registered with GitHub.

```nu
brew install ansible
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
or modify cogmoteGO recipients. Experiment deployment group variables manage
recipients.

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

The inventory enables `StrictHostKeyChecking=accept-new`: Ansible automatically
records an unknown host key on its first connection, but fails if a recorded key
subsequently changes.

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
After the mount starts, `/home/pi/server` is added as the `mxbi-server`
cogmoteGO trusted Samba root and the cogmoteGO user service is restarted.

## Experiment Deployment

`experiment.yml` is a separate experiment deployment entrypoint. It assumes
Samba, GitHub SSH, cogmoteGO, and uv have already been configured; it does not
provision any of them.

Experiment groups are children of `mxbi_experiments` in the inventory. `group1`
contains `mxbi1` through `mxbi5` and deploys `GNGSiD`; `group2` contains
`mxbi6` through `mxbi10` and deploys `self-initiated-discriminate`. Group names
are independent from experiment names. Each group has a group-variable file,
such as `group_vars/group1.yml`:

```yaml
mxbi_experiment_name: GNGSiD
mxbi_experiment_repository: git@github.com:CHiPmxbi/GNGSiD.git
mxbi_experiment_cogmotego_email_recipients:
  - YHu@dpz.eu
```

Replace the repository URL with the actual repository, then run:

```nu
ansible-playbook experiment.yml --limit group1
ansible-playbook experiment.yml --limit mxbi1 --check --diff
```

The playbook first syncs `git@github.com:CHiPmxbi/mxbi_share_config.git` to
`~/.config/mxbi`, then syncs the experiment repository to `~/<exp>`, creates
`~/<exp>/data`, and adds it as the cogmoteGO `mxbi-data` source root. It also deploys and enables
the user-level `mxbi-experiment.service`, which runs `uv run main.py` from the
repository root. Deployment stops this service while keeping it enabled, so it
must be started manually. A device has only this fixed-name experiment service.
Existing repositories are updated to `main`. If Git-tracked files have local,
uncommitted changes, the playbook preserves them, reports the condition, and
skips updating that repository. Untracked files such as `data/` do not block a
switch.
The shared configuration repository uses the same local-change protection. If
`~/.config/mxbi` exists but is not a Git repository, deployment stops instead
of overwriting it.
Each experiment group maintains its authoritative subscriber list with
`mxbi_experiment_cogmotego_email_recipients`; deployment removes recipients
outside the current group and adds missing recipients.
