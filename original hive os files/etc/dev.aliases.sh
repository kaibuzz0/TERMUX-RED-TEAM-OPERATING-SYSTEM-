# Pretty ls/cat
alias ls='eza --group-directories-first --icons=auto -F'
alias ll='eza -alh --group-directories-first --icons=auto -F'
alias la='eza -a --icons=auto -F'
alias cat='bat --paging=never'
# Find/grep
alias ff='fd'
alias rgp='rg -n --pretty --hidden --glob "!.git"'
# fzf helpers
alias fh='history | fzf'
alias fv='fzf'
# Git sane
alias gs='git status -sb'
alias ga='git add -A'
alias gc='git commit -m'
alias gp='git push'
alias gl='git log --oneline --graph --decorate -20'
# Python shorthand
alias py='python'
