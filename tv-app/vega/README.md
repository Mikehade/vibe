# Vibe on Fire TV (Vega OS)

The TV app is a thin React Native for Vega shell that hosts the Vibe web app in Amazon's
`@amazon-devices/webview` WebView. All UI, focus handling and remote keys live in the web app
(`/frontend`), so one codebase runs on Vega OS, Fire OS (Silk browser) and desktop browsers.

## What you need
- Apple silicon Mac (M1 is fine) with **Rosetta 2**: `softwareupdate --install-rosetta --agree-to-license`
- Node.js 18+ and VS Code
- The Vega SDK + Vega Studio extension: https://developer.amazon.com/docs/vega/0.23/install-vega-sdk.html
  (installer: `curl -fsSL https://sdk-installer.vega.labcollab.net/get_vvm.sh | bash`)
- Your deployed Vibe URL (from `deploy/aws/deploy.sh`)

## Steps (about 20 minutes the first time)
1. **Create the project** in VS Code → Vega Studio → `+` → template **hello-world**,
   name `VibeTV`, package `com.vibe.tv`. (CLI alternative in `setup.sh`.)
2. **Turn it into Vibe:**
   ```bash
   ./tv-app/vega/setup.sh ~/path/to/VibeTV https://YOUR-DISTRIBUTION.cloudfront.net
   ```
3. **Build and run** from Vega Studio: build (Debug) → press ▶ on *VirtualDevice:Tv* → press ▶ on *VibeTV*.
4. Use the simulator's remote (arrow keys, Enter, Back) — everything is D-pad navigable.

## Recording the demo
Record the Vega Virtual Device window (macOS: `Cmd+Shift+5`). The hackathon rules accept the
Fire TV/Vega simulator for the Fire TV track.

## Remote keys
| Remote | Web app |
|---|---|
| D-pad | spatial focus navigation |
| Select | activate |
| Back | close dialog / previous screen / exit at home |
| Play/Pause | "Start watching" the focused pick |
| Menu | Settings |

## Troubleshooting
- **White screen / can't reach Vibe:** check the URL in `src/config.ts`; open it in a desktop browser first.
- **Back key does nothing:** keep `allowSystemKeyEvents={true}` on the WebView. The shell also forwards
  hardware back as a `vibe:back` event, and the web app de-duplicates.
- **Local testing without AWS:** run `scripts/dev.sh` and use `http://<your-mac-LAN-IP>:5173` as the URL.
