# CHiPmxbi Setup

Provisioning and setup tools for mxbi experiment workstations, run from a control machine. Once installed, `just` commands cover device configuration, experiment deployment, and routine updates.

## Installation and Initial Setup

### Prerequisites

- Control machine: macOS / Linux (Ansible does not support Windows).
- Ansible and just installed, with SSH access to the target machines.

> Run this repository only from a control machine; do not clone it onto target devices.

### Install Ansible and collections

```sh
# macOS (Homebrew)
brew install ansible ansible-lint just

# Debian / Ubuntu and other Linux (ansible can also be installed with pipx)
sudo apt install ansible
pipx install ansible-lint
```

`just` (command runner): prefer brew / apt when available, otherwise install from <https://github.com/casey/just>.

```sh
ansible-galaxy collection install -r requirements.yml
```

### Initial configuration (admin)

The files below are Git-ignored and exist only on this machine; Vault files must stay encrypted. Never write or commit plaintext copies.

#### 1. Inventory

```sh
cp inventory/hosts.yml.example inventory/hosts.yml
```

Default groups: `group1` = `mxbi[1:5]`, `group2` = `mxbi[6:10]`, plus the dev machine `mxbidev`. Host names are OpenSSH aliases; connection parameters come from the `Host mxbi*` block in `~/.ssh/config` (`HostName %h.local`, user `pi`, `IdentityFile ~/.ssh/mxbi`), so inventory does not repeat them. Inventory enables `StrictHostKeyChecking=accept-new` (an unknown host key is recorded on first connection; a recorded key that changes fails the run).

#### 2. GitHub credentials Vault (loaded by the `github` tag)

```sh
cp vault/mxbi/github.yml.example vault/mxbi/github.yml
ansible-vault encrypt vault/mxbi/github.yml
ansible-vault edit vault/mxbi/github.yml
```

Use `ansible-vault edit` to replace the placeholder in `vault_github_ssh_private_key`.

#### 3. cogmoteGO email Vault (enabled by default)

First check the three variables in `roles/rpi_mxbi_baseline/defaults/main.yml` (defaults are already set):

- `rpi_mxbi_baseline_cogmotego_email_address`
- `rpi_mxbi_baseline_cogmotego_email_smtp_host`
- `rpi_mxbi_baseline_cogmotego_email_smtp_port`

Then create and encrypt the password Vault:

```sh
cp vault/mxbi/cogmotego_email.yml.example vault/mxbi/cogmotego_email.yml
ansible-vault encrypt vault/mxbi/cogmotego_email.yml
ansible-vault edit vault/mxbi/cogmotego_email.yml
```

Replace `vault_cogmotego_email_password` with the real email password. This module does not read or modify cogmoteGO recipients (subscribers are managed by the experiment deployment group variables) and prepares the login keyring before storing the password.

#### 4. Samba Vault (optional, loaded by the `samba` tag)

```sh
cp vault/mxbi/samba.yml.example vault/mxbi/samba.yml
ansible-vault encrypt vault/mxbi/samba.yml
ansible-vault edit vault/mxbi/samba.yml
```

Replace `vault_samba_password` with the real password for `anw-mxbisetup`.

## Common commands

Once configuration is ready, day-to-day work is just two commands covering most operations:

### 1. Full device configuration

```sh
# All mxbi devices (default target)
just baseline-all
# A single device
just baseline-all mxbi8
```

Runs a full configuration on mxbi devices: system packages, HiFiBerry Amp2, Linuxbrew, GitHub SSH credentials, Zsh, cogmoteGO with email, MediaMTX, and VNC, including the `never`-tagged parts (Samba) that are skipped by default. Requires the Vault password; idempotent and safe to re-run; use `just baseline-check mxbi1` to preview the changes.

### 2. Deploy experiments

```sh
# All devices
just exp mxbi
# A single device
just exp mxbi8
```

Deploys experiments to devices according to group variables. Devices must have a baseline first; preview the changes with `just exp-check mxbi1`.

`experiment.yml` is the experiment deployment entry point and assumes Samba, GitHub SSH, cogmoteGO, and uv are already in place; it does not provision any of them. Experiment groups live under `mxbi_experiments` in the inventory, and group names are independent from experiment names. Each group has a group-variable file, e.g. `group_vars/group1.yml`:

```yaml
mxbi_experiment_name: <experiment-name>
mxbi_experiment_repository: git@github.com:<org>/<experiment-repo>.git
mxbi_experiment_uv_sync: true
mxbi_experiment_cogmotego_email_recipients:
  - <subscriber-email>
```

## Other commands

### Selective runs (tags)

To configure only part of the stack, use `--tags` (passed through to Ansible). The most common one is `update`: only upgrades APT and Homebrew packages, loads no Vault, and only prompts for the sudo password:

```sh
just baseline mxbi1 --tags update
```

Other common examples:

```sh
just baseline mxbi1 --tags shell
just baseline mxbi1 --tags 'system,homebrew'
just baseline mxbi1 --tags github
just baseline mxbi5 --tags cogmotego_email
just baseline mxbi5 --tags samba
```

| tag               | Purpose                                                                                                                                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `system`          | System packages                                                                                                                                                                                                                               |
| `hifiberry`       | HiFiBerry Amp2 configuration                                                                                                                                                                                                                  |
| `homebrew`        | Linuxbrew and managed formulae                                                                                                                                                                                                                |
| `github`          | GitHub SSH credentials (loads the GitHub Vault)                                                                                                                                                                                               |
| `shell`           | Zsh configuration                                                                                                                                                                                                                             |
| `cogmotego`       | cogmoteGO                                                                                                                                                                                                                                     |
| `cogmotego_email` | cogmoteGO email (loads the email Vault)                                                                                                                                                                                                       |
| `mediamtx`        | MediaMTX                                                                                                                                                                                                                                      |
| `desktop`         | Desktop and VNC                                                                                                                                                                                                                               |
| `samba`           | Samba mount (`never` tag, skipped by default; loads the Samba Vault, mounts `//infortrend-storage/Neurowissenschaften/AuditorischeNeurowissenschaften/Projekte/MXBI/data/<hostname>` at `/home/pi/server`, registers the `mxbi-server` trusted root, and restarts the cogmoteGO user service) |
| `update`          | Only APT cache refresh and safe upgrade plus Homebrew formula upgrade (loads no Vault)                                                                                                                                                        |

Platform validation and user fact initialization use the `always` tag and run before any selective execution.

### All commands

`just` recipe arguments are passed through to Ansible. Recipes that load a Vault prompt for the Vault password; `just update` loads no Vault and only prompts for the sudo password.

| Command                            | Purpose                                | Vault password needed |
| ---------------------------------- | -------------------------------------- | --------------------- |
| `just install`                     | Install Ansible collections            | No                    |
| `just check`                       | Lint + syntax-check both playbooks     | No                    |
| `just inventory`                   | Show inventory groups and hosts        | No                    |
| `just tags`                        | List baseline playbook tags            | No                    |
| `just baseline [host/group]`       | Full device configuration (default: all mxbi) | Yes            |
| `just baseline-all [host/group]`   | Full configuration including `never` tags (e.g. samba) | Yes |
| `just baseline-check <host/group>` | Configuration check mode (`--check --diff`) | Yes            |
| `just exp <host/group>`            | Deploy experiments                     | No                    |
| `just exp-check <host/group>`      | Experiment deployment check mode       | No                    |
| `just samba <host/group>`          | Mount Samba                            | Yes                   |
| `just update [host/group]`         | Only upgrade APT and Homebrew packages | sudo only             |

## FAQ

- **Prompted for a Vault password**: the Vault password is kept by the team admin; ask them for it.
- **Cannot reach a device**: first check `ssh -G mxbi1` (HostName / User / IdentityFile) and confirm that `~/.ssh/mxbi` exists and is registered on the device.
- **Collections missing**: re-run `just install`.
