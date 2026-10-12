# Source this file from ~/.zshrc to opt in to metadata-only terminal activity.
# ASCM never stores shell command text or terminal output.
typeset -g _ASCM_LAST_COMMAND=""
typeset -g _ASCM_HOOK_FILE="${(%):-%N}"
typeset -g _ASCM_HOOK_ROOT="$(cd "$(dirname "$_ASCM_HOOK_FILE")/.." && pwd)"
_ascm_zsh_preexec() { _ASCM_LAST_COMMAND="$1" }
_ascm_zsh_precmd() {
  local _ascm_status=$?
  local _ascm_root="${ASCM_WATCH_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if command -v python3 >/dev/null 2>&1 && [[ -n "$_ascm_root" ]]; then
    printf '%s' "$_ASCM_LAST_COMMAND" | PYTHONPATH="$_ASCM_HOOK_ROOT${PYTHONPATH:+:$PYTHONPATH}" ASCM_WATCH_PATH="$_ascm_root" python3 -m orchestrator.mentor.activity_cli \
      --workspace "$_ascm_root" terminal --cwd "$PWD" --command-stdin --exit-code "$_ascm_status" \
      >/dev/null 2>&1 || true
  fi
  _ASCM_LAST_COMMAND=""
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec _ascm_zsh_preexec
add-zsh-hook precmd _ascm_zsh_precmd
