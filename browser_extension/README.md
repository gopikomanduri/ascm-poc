# ASCM browser activity extension (opt-in)

This extension records **hostnames only** for active tabs and navigation. It does not read page contents, titles, paths, query strings, form values, cookies, or clipboard data.

## Install (Chrome on macOS/Linux)

1. Load this folder as an unpacked extension at `chrome://extensions` and enable Developer mode.
2. Copy the extension ID shown by Chrome.
3. From the ASCM checkout, run:

   ```bash
   ASCM_WATCH_PATH=/absolute/path/to/workspace python -m orchestrator.mentor.browser_native_host --install --extension-id YOUR_32_CHARACTER_EXTENSION_ID
   ```

4. Restart Chrome. Remove/disable the extension to stop browser signals.

The host manifest is registered for the exact extension ID and the configured workspace. Hostnames are stored locally in `.ascm_history/activity_events.jsonl` and the sanitized audit log. Do not load this extension into a browser profile where you do not want activity metadata recorded.

Native-host installation support is currently macOS/Linux. Windows native-host registration is not implemented yet. This adapter is not enabled by the ASCM installer automatically.
