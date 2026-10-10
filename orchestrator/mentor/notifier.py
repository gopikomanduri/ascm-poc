#!/usr/bin/env python3
"""
ASCM Cross-Platform Notifier & Ambient Dialog Utility
Provides native desktop notifications & interactive prompt dialogs across:
- macOS (osascript native AppleScript / System Events)
- Windows (PowerShell BurntToast / WScript.Shell / MsgBox)
- Linux (notify-send / zenity / kdialog)
- Headless / Fallback (terminal broadcast / ANSI box)
"""

import os
import sys
import shutil
import subprocess
import logging
from typing import Optional

logger = logging.getLogger("ASCMNotifier")


class CrossPlatformNotifier:
    """Universal notification and dialog engine across macOS, Windows, and Linux."""

    @staticmethod
    def notify(title: str, message: str, app_name: str = "ASCM Mentor") -> bool:
        """Send a native OS banner/toast notification."""
        print(f"\n💡 [{app_name.upper()}] {title}: {message}")

        platform = sys.platform.lower()

        # 1. macOS (Darwin)
        if platform.startswith("darwin"):
            try:
                safe_title = title.replace('"', '\\"')
                safe_msg = message.replace('"', '\\"')
                safe_app = app_name.replace('"', '\\"')
                apple_script = (
                    f'display notification "{safe_msg}" with title "{safe_title}" subtitle "{safe_app}"'
                )
                res = subprocess.run(["osascript", "-e", apple_script], capture_output=True, timeout=3)
                return res.returncode == 0
            except Exception as e:
                logger.debug(f"macOS notification failed: {e}")

        # 2. Windows (win32 / cygwin)
        elif platform.startswith("win"):
            # Try Windows PowerShell BurntToast or balloon tooltip
            try:
                ps_script = f"""
                [reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null
                $notify = new-object system.windows.forms.notifyicon
                $notify.icon = [system.drawing.systemicons]::Information
                $notify.visible = $true
                $notify.showballoontip(10, '{title}', '{message}', [system.windows.forms.tooltipicon]::Info)
                Start-Sleep -Seconds 2
                $notify.dispose()
                """
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    capture_output=True,
                    timeout=5,
                )
                return res.returncode == 0
            except Exception as e:
                logger.debug(f"Windows notification failed: {e}")

        # 3. Linux / BSD
        elif platform.startswith("linux") or "bsd" in platform:
            if shutil.which("notify-send"):
                try:
                    res = subprocess.run(
                        ["notify-send", "-a", app_name, title, message],
                        capture_output=True,
                        timeout=3,
                    )
                    return res.returncode == 0
                except Exception as e:
                    logger.debug(f"Linux notify-send failed: {e}")

        return False

    @staticmethod
    def prompt_dialog(prompt_text: str, default_text: str = "", title: str = "ASCM Proactive Mentor") -> Optional[str]:
        """
        Pops up an interactive modal dialog over whatever app the user is working in
        (Excel, Browser, IDE), allowing them to respond.
        Falls back to terminal input if GUI dialogs are unavailable or cancelled.
        """
        platform = sys.platform.lower()

        # 1. macOS
        if platform.startswith("darwin"):
            try:
                safe_p = prompt_text.replace('"', '\\"')
                safe_d = default_text.replace('"', '\\"')
                safe_t = title.replace('"', '\\"')
                apple_script = f'''
                display dialog "{safe_p}" default answer "{safe_d}" with title "{safe_t}" buttons {{"Cancel", "Confirm"}} default button "Confirm"
                '''
                res = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True, timeout=45)
                if res.returncode == 0 and "text returned:" in res.stdout:
                    return res.stdout.split("text returned:")[-1].strip()
            except Exception as e:
                logger.debug(f"macOS dialog failed: {e}")

        # 2. Windows
        elif platform.startswith("win"):
            try:
                ps_script = f"""
                Add-Type -AssemblyName Microsoft.VisualBasic
                [Microsoft.VisualBasic.Interaction]::InputBox('{prompt_text}', '{title}', '{default_text}')
                """
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception as e:
                logger.debug(f"Windows InputBox failed: {e}")

        # 3. Linux (Zenity or Kdialog)
        elif platform.startswith("linux") or "bsd" in platform:
            if shutil.which("zenity"):
                try:
                    res = subprocess.run(
                        ["zenity", "--entry", f"--title={title}", f"--text={prompt_text}", f"--entry-text={default_text}"],
                        capture_output=True,
                        text=True,
                        timeout=45,
                    )
                    if res.returncode == 0:
                        return res.stdout.strip()
                except Exception as e:
                    logger.debug(f"Linux zenity failed: {e}")
            elif shutil.which("kdialog"):
                try:
                    res = subprocess.run(
                        ["kdialog", f"--title={title}", f"--inputbox={prompt_text}", default_text],
                        capture_output=True,
                        text=True,
                        timeout=45,
                    )
                    if res.returncode == 0:
                        return res.stdout.strip()
                except Exception as e:
                    logger.debug(f"Linux kdialog failed: {e}")

        # Fallback to terminal input
        try:
            return input(f"\n💡 [{title.upper()}] {prompt_text} [{default_text}]: ").strip() or default_text
        except (EOFError, KeyboardInterrupt):
            return default_text

    @staticmethod
    def confirm_dialog(text: str, buttons=("No", "Allow once", "Always allow"), title: str = "ASCM Mentor") -> Optional[str]:
        """
        Ask the user to pick one button. Returns the chosen label, or None if the dialog
        could not be shown / was dismissed (callers must treat None as "no").
        Native dialog on macOS; terminal prompt elsewhere when a TTY is attached.
        """
        if sys.platform.lower().startswith("darwin"):
            try:
                safe_t = text.replace("\\", "\\\\").replace('"', '\\"')
                btns = ", ".join('"%s"' % b for b in buttons)
                script = (f'display dialog "{safe_t}" with title "{title}" buttons {{{btns}}} '
                          f'default button "{buttons[0]}" cancel button "{buttons[0]}"')
                res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=120)
                if res.returncode == 0 and "button returned:" in res.stdout:
                    return res.stdout.split("button returned:")[-1].split(",")[0].strip()
                return None
            except Exception as e:
                logger.debug(f"macOS confirm dialog failed: {e}")
                return None

        if sys.stdin and sys.stdin.isatty():
            try:
                opts = "/".join(f"{i}={b}" for i, b in enumerate(buttons))
                ans = input(f"\n💡 [{title.upper()}] {text}\n   Choose [{opts}] (default 0): ").strip() or "0"
                return buttons[int(ans)]
            except (EOFError, KeyboardInterrupt, ValueError, IndexError):
                return None
        return None


if __name__ == "__main__":
    CrossPlatformNotifier.notify("ASCM Mentor", "Universal cross-platform notification test")
    val = CrossPlatformNotifier.prompt_dialog("What are you building right now?", "Real-time payments API")
    print("User answered:", val)
