#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Bootstrap
# ============================================================

export DEBIAN_FRONTEND=noninteractive
export HOMEBREW_NO_ASK=1

# The script uses sudo only for privileged operations, so running the whole
# script as root would create user-level symlinks and shell changes for root.
if [ "$(id -u)" -eq 0 ]; then
  printf 'Do not run this script as root. Run it as a normal user.\n' >&2
  exit 1
fi

# Resolve user paths once. These are used for dotfile symlinks and chsh.
target_user="$(id -un)"
target_home="$(getent passwd "$target_user" | cut -d: -f6)"
dotfiles_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"


# ============================================================
# System
# ============================================================

# System updates
sudo apt-get update
sudo apt-get upgrade -y

# Core dependencies
sudo apt-get install -y \
  portaudio19-dev \
  pipewire-audio \
  dbus-daemon \
  gnome-keyring \
  libglib2.0-bin \
  libsecret-tools


# ============================================================
# HiFiBerry Amp2
# ============================================================

boot_config="/boot/firmware/config.txt"

# The HiFiBerry overlay is inserted below [all], so fail loudly if the expected
# Raspberry Pi boot config shape is not present.
if ! grep -Fxq '[all]' "$boot_config"; then
  printf 'Missing [all] section in %s\n' "$boot_config" >&2
  exit 1
fi

# Disable onboard audio so the HiFiBerry Amp2 becomes the active audio device.
sudo perl -0pi -e 's/^dtparam=audio=on$/# dtparam=audio=on/m' "$boot_config"
sudo perl -0pi -e 's/^dtoverlay=vc4-kms-v3d$/dtoverlay=vc4-kms-v3d,noaudio/m' "$boot_config"

# Keep the managed block idempotent and easy to identify in config.txt.
if ! grep -Fq '# BEGIN mxbi HiFiBerry Amp2' "$boot_config"; then
  sudo perl -0pi -e 's/^\[all\]\n/[all]\n# BEGIN mxbi HiFiBerry Amp2\ndtoverlay=hifiberry-dacplus-std\n# END mxbi HiFiBerry Amp2\n/m' "$boot_config"
fi


# ============================================================
# Homebrew
# ============================================================

# Homebrew dependencies
sudo apt-get install -y build-essential bubblewrap procps curl file git

# Homebrew installation
if ! command -v brew >/dev/null 2>&1; then
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Homebrew environment
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv zsh)"

# Homebrew packages
brew install \
  gh \
  lazygit \
  mediamtx \
  uv


# ============================================================
# GitHub
# ============================================================

# SSH 密钥和 known_hosts 由外部提供（未来交给 Ansible），此处仅选择并验证 SSH。
gh config set git_protocol ssh --host github.com
if ! GIT_SSH_COMMAND="ssh -o BatchMode=yes" \
  git ls-remote git@github.com:CHiPmxbi/mxbi_share_config.git HEAD >/dev/null; then
  printf '%s\n' \
    'GitHub SSH 认证失败，请检查 SSH 密钥、ssh-agent、known_hosts 和仓库权限。' >&2
  exit 1
fi


# ============================================================
# Base Shell Environment
# ============================================================

# Install zsh
sudo apt-get install -y zsh
sudo apt-get install -y kitty-terminfo

# Link zsh config
zsh_path="$(command -v zsh)"
ln -sfn "$dotfiles_dir/.zshrc" "$target_home/.zshrc"

# Set default shell
if [ "$(getent passwd "$target_user" | cut -d: -f7)" != "$zsh_path" ]; then
  sudo chsh -s "$zsh_path" "$target_user"
fi

# Install prompt, completion, plugins, and terminal fonts used by .zshrc.
brew install \
  starship \
  carapace \
  zsh-autosuggestions \
  zsh-syntax-highlighting \
  font-maple-mono-nf-cn \
  font-noto-color-emoji

# Desktop config
mkdir -p "$target_home/.config/lxterminal"
ln -sfn "$dotfiles_dir/.config/lxterminal/lxterminal.conf" "$target_home/.config/lxterminal/lxterminal.conf"


# ============================================================
# User Services
# ============================================================

# Keep the user service manager running when no interactive session is active.
sudo loginctl enable-linger "$target_user"

# Create an empty-password login keyring only when one does not already exist.
keyring_dir="$target_home/.local/share/keyrings"
if [ ! -e "$keyring_dir/login.keyring" ]; then
  mkdir -p "$keyring_dir"
  dbus-run-session -- sh -eu -c '
    eval "$(printf "" | gnome-keyring-daemon --unlock --components=secrets)"
    gdbus call --session \
      --dest org.freedesktop.secrets \
      --object-path /org/freedesktop/secrets \
      --method org.freedesktop.Secret.Service.SetAlias \
      default /org/freedesktop/secrets/collection/login >/dev/null
  '
fi

# Install cogmoteGO with its official installer and register its user service.
curl -sS https://raw.githubusercontent.com/cagelab/cogmoteGO/main/install.sh | sh
cogmotego_path="$target_home/.local/bin/cogmoteGO"
if [ ! -f "$target_home/.config/systemd/user/cogmoteGO.service" ]; then
  "$cogmotego_path" service -u
fi
"$cogmotego_path" service start -u

# 安装唯一的 MediaMTX Raspberry Pi Camera 配置。
mediamtx_config_dir="$target_home/.config/mediamtx"
systemd_user_dir="$target_home/.config/systemd/user"
mkdir -p "$mediamtx_config_dir" "$systemd_user_dir"
ln -sfn "$dotfiles_dir/services/mediamtx.yml" "$mediamtx_config_dir/mediamtx.yml"
ln -sfn "$dotfiles_dir/services/mediamtx.service" "$systemd_user_dir/mediamtx.service"
systemctl --user daemon-reload
systemctl --user enable --now mediamtx.service


# ============================================================
# Raspberry Pi Desktop
# ============================================================

# VNC
sudo raspi-config nonint do_vnc 0
