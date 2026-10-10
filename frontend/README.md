# Vibe TV web app (frontend)

React + Vite + Tailwind, built for the 10-foot screen and a D-pad remote.
Runs inside the Vega OS WebView shell (`/tv-app/vega`), Fire TV's Silk browser, or any desktop browser.

- `src/lib/focus/` — spatial navigation, back handling, focus scopes (also published as `/packages/tv-dpad-focus`)
- `src/stores/plan.ts` — applies the NDJSON stream to the screen as it arrives
- `src/screens/` — Home, Plan, Watch (check-in), Feedback, Couch Mode, Join (phone), History, Settings, Onboarding
- Sizes are in `rem`, and `html.tv { font-size: calc(100vw / 120) }` keeps the layout identical from 960×540 to 4K
- Fonts are bundled (`@fontsource`), so the TV makes no font requests

Dev: `npm run dev` (proxies `/api` and `/mcp` to `VITE_PROXY_TARGET`, default `http://localhost:8000`).
