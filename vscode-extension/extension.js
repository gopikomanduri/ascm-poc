const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const { execFile } = require("child_process");

function findAscmRepo(extensionPath, configuredPath) {
  if (configuredPath && configuredPath.trim()) return path.resolve(configuredPath.trim());
  const candidate = path.resolve(extensionPath, "..");
  if (fs.existsSync(path.join(candidate, "orchestrator", "mentor", "activity_cli.py"))) {
    return candidate;
  }
  return null;
}

function activate(context) {
  const output = vscode.window.createOutputChannel("ASCM Project Context");
  context.subscriptions.push(output);
  let lastProject = null;
  let inFlight = false;

  function recordProject(uri) {
    const folder = uri
      ? vscode.workspace.getWorkspaceFolder(uri)
      : (vscode.workspace.workspaceFolders || [])[0];
    if (!folder) return;
    const projectPath = path.resolve(folder.uri.fsPath);
    if (projectPath === lastProject || inFlight) return;

    const config = vscode.workspace.getConfiguration("ascm");
    const repoPath = findAscmRepo(context.extensionPath, config.get("repoPath", ""));
    if (!repoPath) {
      output.appendLine("Set ascm.repoPath to the ASCM checkout; no document content was read.");
      return;
    }
    const configuredWorkspace = config.get("workspacePath", "") || process.env.ASCM_WATCH_PATH;
    const workspacePath = path.resolve(configuredWorkspace || projectPath);
    const pythonPath = config.get("pythonPath", "python3");
    inFlight = true;
    execFile(
      pythonPath,
      [
        "-m", "orchestrator.mentor.activity_cli",
        "--workspace", workspacePath,
        "project-activated",
        "--project-path", projectPath
      ],
      { cwd: repoPath, timeout: 5000, windowsHide: true },
      (error) => {
        inFlight = false;
        if (error) {
          output.appendLine("Project activation metadata was not recorded (" + (error.code || "adapter_error") + ").");
          return;
        }
        lastProject = projectPath;
        output.appendLine("Recorded project activation metadata for the active workspace.");
      }
    );
  }

  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(editor => {
      if (editor && editor.document && editor.document.uri.scheme === "file") {
        recordProject(editor.document.uri);
      }
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
      const editor = vscode.window.activeTextEditor;
      recordProject(editor && editor.document ? editor.document.uri : undefined);
    })
  );

  const editor = vscode.window.activeTextEditor;
  recordProject(editor && editor.document ? editor.document.uri : undefined);
}

function deactivate() {}

module.exports = { activate, deactivate };
