# ============================================================
# Basic settings
# ============================================================

# Use Emacs-style key bindings
bindkey -e

# History
HISTFILE="$HOME/.zsh_history"
HISTSIZE=10000
SAVEHIST=10000

# Ignore duplicate history entries
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_SAVE_NO_DUPS
setopt HIST_REDUCE_BLANKS
setopt SHARE_HISTORY

# Allow entering directory names without cd
setopt AUTO_CD

# Show selection menu during completion
setopt AUTO_MENU
setopt COMPLETE_IN_WORD


# ============================================================
# Homebrew
# ============================================================

eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv zsh)"


# Use Homebrew Neovim as the default editor
export EDITOR='nvim'
export VISUAL='nvim'
export SUDO_EDITOR='nvim'


# ============================================================
# Zsh completion system
# ============================================================

autoload -Uz compinit
compinit

# Make completion matching case-insensitive
zstyle ':completion:*' matcher-list \
  'm:{a-zA-Z}={A-Za-z}' \
  'r:|[._-]=* r:|=*'

# Use menu selection for completion results
zstyle ':completion:*' menu select


# ============================================================
# Carapace
# ============================================================

# Allow Carapace to use completion definitions from other shells
export CARAPACE_BRIDGES='zsh,fish,bash,inshellisense'

source <(carapace _carapace)


# ============================================================
# Starship
# ============================================================

eval "$(starship init zsh)"


# ============================================================
# Zsh plugins
# ============================================================

# Get the Homebrew installation directory
BREW_PREFIX="${HOMEBREW_PREFIX:-$(brew --prefix)}"

# Show gray suggestions based on history
source "$BREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh"

# Use the right arrow key to accept the full suggestion
bindkey '^[[C' autosuggest-accept

# Keep this as close to the end of .zshrc as possible
source "$BREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"

unset BREW_PREFIX
