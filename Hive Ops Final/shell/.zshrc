# --- Hive env ---
[ -f "$HOME/.config/hive/env.sh" ] && . "$HOME/.config/hive/env.sh"

# --- zsh ergonomics ---
setopt interactivecomments
setopt no_nomatch

# --- Starship prompt ---
if command -v starship >/dev/null 2>&1; then
  eval "$(starship init zsh)"
fi

# >>> hive env >>>
[ -r "$HOME/.config/hive/env.sh" ] && . "$HOME/.config/hive/env.sh"
# <<< hive env <<<
