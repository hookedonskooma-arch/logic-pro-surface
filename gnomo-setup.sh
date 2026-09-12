#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  GNOMO setup — one paste. Installs and starts the desk companion.
#
#  What it does:
#   1. Checks macOS (fails honestly elsewhere — the face is AppKit)
#   2. Checks/creates the launchable Gnomo.app (build if missing)
#   3. Ad-hoc codesigns it (TCC grants tie to the signature)
#   4. Compiles the companion router's Python deps (none beyond stdlib)
#   5. Installs the LaunchAgent (launch-at-login, keep-alive)
#   6. Verifies: launchctl state + window on screen
#
#  The mic/speech TCC grant is per-signature: first launch asks, click Allow.
#  Do NOT Rebuild Defaults anywhere; do not touch MELEGI audio buses.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HERE/companion/build/Gnomo.app"
PLIST_SRC="$HERE/companion/app/Info.plist"
AGENT_SRC="$HERE/companion/gnomo-agent.sh"
AGENT_DST="$HOME/Library/LaunchAgents/studio.gnomo.companion.plist"
LABEL="studio.gnomo.companion"
G="$(printf '\033[32m')"; Y="$(printf '\033[33m')"; R="$(printf '\033[31m')"; N="$(printf '\033[0m')"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║        GNOMO — one-paste setup        ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── 1. macOS only ──
if [[ "$(uname)" != "Darwin" ]]; then
  echo "  ${R}✗ macOS required. The companion face is AppKit; it does not exist elsewhere.${N}"
  exit 1
fi
echo "  ${G}✓ macOS $(sw_vers -productVersion)${N}"

# ── 2. Build the app if missing ──
if [[ ! -x "$APP_DIR/Contents/MacOS/Gnomo" ]]; then
  echo "  ${Y}building Gnomo.app (swiftc, one file, no deps)…${N}"
  mkdir -p "$APP_DIR/Contents/MacOS"
  swiftc -o "$HERE/companion/build/Gnomo" "$HERE/companion/main.swift"
  cp "$PLIST_SRC" "$APP_DIR/Contents/Info.plist"
  cp "$HERE/companion/build/Gnomo" "$APP_DIR/Contents/MacOS/Gnomo"
else
  echo "  ${G}✓ Gnomo.app already built${N}"
fi

# ── 3. Ad-hoc signature (TCC identity) ──
codesign --force -s - "$APP_DIR" 2>/dev/null
codesign --verify "$APP_DIR" && echo "  ${G}✓ ad-hoc codesign ok (${LABEL})${N}"

# ── 4. Python side: stdlib only, but prove the CLI runs ──
PYTHON="$(command -v python3)"
if ! PYTHONPATH="$HERE/logic-probe" python3 -c "import gnomo" >/dev/null 2>&1; then
  echo "  ${R}✗ gnomo CLI import failed — is logic-probe/ present?${N}"
  exit 1
fi
echo "  ${G}✓ gnomo CLI imports clean${N}"

# ── 5. LaunchAgent ──
mkdir -p "$HOME/Library/LaunchAgents"
chmod +x "$AGENT_SRC"
sed "s|__REPO_ROOT__|$HERE|g" \
  "$HERE/companion/launchagent.plist" > "$AGENT_DST"
plutil -lint "$AGENT_DST" >/dev/null
UID_N="$(id -u)"
launchctl bootout "gui/$UID_N/$LABEL" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$UID_N" "$AGENT_DST"
sleep 5
if launchctl print "gui/$UID_N/$LABEL" 2>/dev/null | grep -q "state = running"; then
  echo "  ${G}✓ LaunchAgent running${N}"
else
  echo "  ${Y}⚠ LaunchAgent bootstrapped but not yet running — check /tmp/gnomo-launchagent.log${N}"
fi

# ── 6. Verify the face ──
sleep 2
if osascript -e 'tell application "System Events" to exists (processes where name is "Gnomo")' 2>/dev/null | grep -q true; then
  echo "  ${G}✓ the gnome is on the desk${N}"
else
  echo "  ${Y}? window not confirmed — look for the gnome; check /tmp/gnomo-launchagent.log${N}"
fi

echo ""
echo "  Done. First ears use asks for mic + speech — click Allow."
echo "  Reboot test: log out/in — the gnome should greet you unaided."
echo "  Selftest: GNOMO_MUTE=1 $APP_DIR/Contents/MacOS/Gnomo --selftest"
echo ""