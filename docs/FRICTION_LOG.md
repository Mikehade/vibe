# Friction log

Each entry: task, steps, expected vs. actual, severity, workaround, suggestion. Entries 1–5 were observed while
building on Sept 27–28, 2026; **verify them on your machine and add your own as you go** (Vega SDK install,
simulator, deploy, Alexa+). Submissions with friction logs can earn up to a 10% bonus — real, specific entries matter most.

---

### 1. Finding Vega CLI commands for a new web app
- **Task:** create a Vega project from the command line.
- **Steps:** read *Create a Hello World App* (0.23) → it covers only the Vega Studio GUI; the CLI reference found in search is 0.21 and uses `kepler project generate …`.
- **Expected:** GUI and CLI steps on one page with the current command name.
- **Actual:** unclear whether the CLI is `vega` or `kepler` in the current SDK.
- **Severity:** Low
- **Workaround:** used Vega Studio; documented both names in our setup script.
- **Suggestion:** show CLI equivalents next to each GUI step and note the rename.

### 2. Versioned WebView setup page 404s
- **Task:** configure `manifest.toml` for a WebView app.
- **Steps:** opened `https://developer.amazon.com/docs/vega/0.23/set-up-webview`.
- **Expected:** the 0.23 version of the page.
- **Actual:** 404; the 0.21 page exists.
- **Severity:** Low
- **Workaround:** used the 0.21 manifest entries.
- **Suggestion:** redirect missing versioned pages to the latest version.

### 3. Back key and messaging in Vega WebView apps
- **Task:** make the remote's Back button close dialogs in the web app and exit at the home screen.
- **Steps:** read the web app developer guide; it mentions `allowSystemKeyEvents` but not how Back is delivered or whether `onMessage`/`postMessage` work.
- **Expected:** a documented pattern for Back and web → native messages.
- **Actual:** had to support both a DOM key event and a native `BackHandler` injection, and de-duplicate.
- **Severity:** Medium
- **Workaround:** handled both paths; ignore a second Back within 300 ms.
- **Suggestion:** add a "Back button and exit" section with a code sample.

### 4. Testing an MCP server with Alexa+ from outside the US
- **Task:** test our MCP server with Alexa+.
- **Steps:** read the MCP Toolkit overview.
- **Expected:** a way to test from any country (at least in a simulator).
- **Actual:** "The MCP Toolkit is available in the United States."
- **Severity:** High (for non-US participants)
- **Workaround:** tested with MCP Inspector and a scripted MCP client; demo shows the TV reacting live.
- **Suggestion:** open the web simulator to all hackathon participants.

### 5. Letter keys triggering media actions in a TV web app
- **Task:** type a profile name on the onboarding screen.
- **Steps:** typed "Seun"; the "u" never appeared.
- **Expected:** normal typing.
- **Actual:** our remote handler also matched raw Android keyCodes; "u" is keyCode 85, which is KEYCODE_MEDIA_PLAY_PAUSE.
- **Severity:** Medium (our bug, but an easy trap on TV web platforms)
- **Workaround:** only use raw keyCodes when `event.key` is `Unidentified`.
- **Suggestion:** a Vega WebView key-mapping table (which `key` / `keyCode` each remote button produces).

### 6. <your entry — e.g. installing the Vega SDK on Apple silicon>
- **Task:**
- **Steps:**
- **Expected:**
- **Actual:**
- **Severity:**
- **Workaround:**
- **Suggestion:**
