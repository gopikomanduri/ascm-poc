# Source this file from ~/.bashrc to opt in to metadata-only terminal activity.
# ASCM never stores shell command text or terminal output.
_ascm_bash_prompt_hook() {
  local _ascm_status=$?
  local _ascm_root="${ASCM_WATCH_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local _ascm_cmd
  _ascm_cmd=$(HISTTIMEFORMAT= history 1 2>/dev/null | sed 's/^ *[0-9]* *//' || true)
  if command -v python3 >/dev/null 2>&1 && [ -n "$_ascm_root" ]; then
    printf '%s' "$_ascm_cmd" | ASCM_WATCH_PATH="$_ascm_root" python3 -m orchestrator.mentor.activity_cli \
      --workspace "$_ascm_root" terminal --cwd "$PWD" --command-stdin --exit-code "$_ascm_status" \
      >/dev/null 2>&1 || true
  fi
}
case ";$PROMPT_COMMAND;" in
  *";_ascm_bash_prompt_hook;"*) ;;
  *) PROMPT_COMMAND="_ascm_bash_prompt_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac
