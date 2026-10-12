# ASCM Project Context extension

Optional VS Code-compatible extension (also usable in compatible editor forks) that records **which workspace became active**. It does not read document text, selections, terminal output, window titles, or file contents.

## Setup

1. Open this folder in VS Code and run **Developer: Install Extension from Location...** if supported, or package it as a VSIX using your approved packaging process.
2. In settings, set `ascm.repoPath` to the absolute path of the ASCM checkout that contains `orchestrator/mentor/activity_cli.py`.
3. Optionally set `ascm.workspacePath` to the common parent of multiple project repositories. If omitted, events are stored in the active project’s `.ascm_history`.
4. Set `ascm.pythonPath` to a Python executable that can import ASCM. On Windows this may be `python` instead of `python3`.
5. Open a workspace. The extension sends a project activation event only when the active workspace changes.

The extension invokes Python with an argument array (no shell), and only passes the workspace path. No source content or file names are sent. Local filesystem permissions and the configured workspace boundary still apply. Disable the extension to stop IDE activation events.
