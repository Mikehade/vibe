#!/usr/bin/env bash
# Turns a freshly generated Vega "hello-world" project into the Vibe TV app.
#
# Usage:  ./setup.sh <path-to-generated-vega-project> <https://your-vibe-url>
#
# Get the project first (either way works):
#   - VS Code → Vega Studio → "+" → template "hello-world", name VibeTV, package com.vibe.tv
#   - or CLI:  vega project generate --template hello-world --name VibeTV --packageId com.vibe.tv --outputDir VibeTV
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PROJ="${1:?path to generated Vega project}"
URL="${2:?your deployed Vibe URL, e.g. https://d123.cloudfront.net}"

[ -f "$PROJ/package.json" ] || { echo "No package.json in $PROJ — is that the generated Vega project?"; exit 1; }
[ -f "$PROJ/manifest.toml" ] || { echo "No manifest.toml in $PROJ"; exit 1; }

echo "→ Installing the Vega WebView package"
(cd "$PROJ" && npm install @amazon-devices/webview@^3.3.0)

echo "→ Copying the Vibe shell"
mkdir -p "$PROJ/src"
cp "$HERE/src/App.tsx" "$PROJ/src/App.tsx"
sed "s#https://REPLACE_ME.cloudfront.net#${URL}#" "$HERE/src/config.ts" > "$PROJ/src/config.ts"

if ! grep -q "com.amazon.gipc.uuid" "$PROJ/manifest.toml"; then
  echo "→ Adding WebView services to manifest.toml"
  printf "\n" >> "$PROJ/manifest.toml"
  cat "$HERE/manifest.additions.toml" >> "$PROJ/manifest.toml"
fi

cat <<MSG

Done. Next:
  cd "$PROJ"
  npm install
  vega build -b Debug                 # or the build button in Vega Studio
  vega virtual-device start           # Vega Virtual Device (the Fire TV simulator)
  vega run-app                        # or press ▶ on the project in Vega Studio

If your SDK uses the older 'kepler' CLI name, replace 'vega' with 'kepler' above.
MSG
