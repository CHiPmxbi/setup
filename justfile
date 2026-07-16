# List available recipes.
default:
    @just --list

# Install the required Ansible collections.
install:
    ansible-galaxy collection install -r requirements.yml

# Lint playbooks and roles.
lint:
    ansible-lint rpi-mxbi-baseline.yml experiment.yml

# Check both playbooks for syntax errors.
syntax:
    ansible-playbook rpi-mxbi-baseline.yml --syntax-check
    ansible-playbook experiment.yml --syntax-check

# Run all local static checks.
check: lint syntax

# Display inventory groups and hosts.
inventory:
    ansible-inventory --graph

# List tags provided by the baseline playbook.
tags:
    ansible-playbook rpi-mxbi-baseline.yml --list-tags

# Prepare the baseline for a host or group; defaults to all mxbi hosts.
baseline target='mxbi' *args:
    ansible-playbook rpi-mxbi-baseline.yml --limit {{target}} --ask-vault-pass {{args}}

# Check the baseline for a host or group; defaults to all mxbi hosts.
baseline-check target='mxbi' *args:
    ansible-playbook rpi-mxbi-baseline.yml --limit {{target}} --ask-vault-pass --check --diff {{args}}

# Deploy an experiment to a host or group; extra arguments are passed to Ansible.
exp target *args:
    ansible-playbook experiment.yml --limit {{target}} {{args}}

# Check experiment deployment for a host or group; extra arguments are passed to Ansible.
exp-check target *args:
    ansible-playbook experiment.yml --limit {{target}} --check --diff {{args}}

# Configure the Samba mount for a host or group; extra arguments are passed to Ansible.
samba target *args:
    ansible-playbook rpi-mxbi-baseline.yml --limit {{target}} --tags samba --ask-vault-pass {{args}}
