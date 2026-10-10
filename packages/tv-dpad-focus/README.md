# tv-dpad-focus

D-pad spatial navigation for React web apps that run on TVs — Fire TV (Vega OS WebView, Fire OS / Silk),
Android TV WebViews, and plain desktop browsers (arrow keys + mouse hover). No dependencies, ~4 KB.

Built for [Vibe](../../README.md) during the Amazon Developer Hackathon (2026) and extracted as a standalone package.

## Why
TV remotes send arrow keys, not Tab. Most "TV navigation" libraries need every element registered
in a tree with ids and parent/child wiring. This one is geometric: mark elements focusable, and the
nearest element in the pressed direction wins — the way Fire TV's own launcher feels.

It also handles the fiddly platform bits:
- **Back**: `Escape`, `GoBack`, `BrowserBack`, Backspace (outside inputs), raw keyCodes 4 / 27 / 461 / 10009,
  and a `vibe:back` window event a native shell can dispatch. Duplicate backs within 300 ms are ignored.
- **Raw keyCodes only when `key` is `Unidentified`** — so typing "u" in a text box doesn't trigger
  Android's media Play/Pause (keyCode 85). (A real bug we hit.)
- **Select** clicks the focused element; **Play/Pause** and **Menu** become `vibe:play` / `vibe:menu` events.
- **Focus scopes** for modals (focus is trapped in the top-most scope) and autofocus with `data-autofocus`.
- **Rails**: wrap a row in `data-focus-group` so left/right stays in the row.
- **Mouse hover** focuses too, so judges on laptops see the same UI.

## Use
```tsx
import { FocusProvider, FocusScope, focusProps, useBack } from 'tv-dpad-focus';

function Screen() {
  useBack(() => { history.back(); return true; });
  return (
    <FocusScope>
      <button {...focusProps} data-autofocus>Play</button>
      <div data-focus-group className="rail">
        {items.map((i) => <button key={i.id} {...focusProps} data-scroll-inline="center">{i.title}</button>)}
      </div>
    </FocusScope>
  );
}

export default () => (
  <FocusProvider onRootBack={() => window.close()}>
    <Screen />
  </FocusProvider>
);
```

Style focus with plain CSS: `[data-focusable]:focus { outline: 3px solid white; transform: scale(1.05); }`

## Scaling for 10-foot UIs
Fire TV WebViews often report 960×540 CSS pixels. Size everything in `rem` and set
`html { font-size: calc(100vw / 120); }` — 16 px at 1920 wide, 8 px at 960 — and layouts stay identical.

## License
MIT
