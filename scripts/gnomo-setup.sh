#!/usr/bin/env bash
# One paste, no decisions. Finds or clones the repo, builds an isolated venv,
# then runs the MCU walkthrough.
#
# Why a venv: modern macOS Pythons are PEP 668 "externally managed", so a plain
# `pip3 install mido` dies with a wall of red text that looks like user error.
# It is not. A venv sidesteps it completely and touches no system Python.
#
# This script never edits a Logic project and never touches your songs.

set -euo pipefail

BRANCH="claude/logic-pro-gnome-companion-vsp930"
REPO_URL="https://github.com/hookedonskooma-arch/logic-pro-surface.git"
DEFAULT_DIR="$HOME/logic-pro-surface"
VENV_NAME=".venv-gnomo"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }
die() { printf '\n\033[1mStopped:\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. python ------------------------------------------------------------
command -v python3 >/dev/null 2>&1 || die \
  "no python3. Install Xcode command line tools first:  xcode-select --install"

# --- 2. find or clone the repo -------------------------------------------
if git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_DIR="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
elif [ -d "$DEFAULT_DIR/.git" ]; then
  REPO_DIR="$DEFAULT_DIR"
else
  say "Cloning the repo to $DEFAULT_DIR"
  command -v git >/dev/null 2>&1 || die "no git. Run:  xcode-select --install"
  git clone "$REPO_URL" "$DEFAULT_DIR"
  REPO_DIR="$DEFAULT_DIR"
fi
cd "$REPO_DIR"
say "Repo: $REPO_DIR"

# --- 3. get on the branch -------------------------------------------------
if [ -n "$(git status --porcelain)" ]; then
  note "You have uncommitted changes. Leaving them alone and not switching branches."
  note "Current branch: $(git rev-parse --abbrev-ref HEAD)"
else
  git fetch origin "$BRANCH" --quiet 2>/dev/null || note "could not reach GitHub; using the local copy"
  git checkout "$BRANCH" --quiet 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH" --quiet 2>/dev/null || true
  git merge --ff-only "origin/$BRANCH" --quiet 2>/dev/null || true
  note "Branch: $(git rev-parse --abbrev-ref HEAD)"
fi

# --- 4. isolated venv -----------------------------------------------------
if [ ! -d "$VENV_NAME" ]; then
  say "Building an isolated Python (this does not touch your system Python)"
  python3 -m venv "$VENV_NAME" || die \
    "could not create a venv. Try:  python3 -m pip install --user virtualenv"
fi
PY="$REPO_DIR/$VENV_NAME/bin/python"
[ -x "$PY" ] || die "venv looks broken. Delete $VENV_NAME and run this again."

"$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
if ! "$PY" -c "import mido" >/dev/null 2>&1; then
  say "Installing the MIDI libraries"
  if ! "$PY" -m pip install --quiet mido python-rtmidi; then
    note "MIDI install failed. Continuing anyway - the walkthrough degrades honestly"
    note "and will tell you what it cannot check."
  fi
fi

# --- 5. a `gnomo` command so PYTHONPATH is never typed again --------------
cat > "$REPO_DIR/gnomo" << 'SHIM'
#!/usr/bin/env bash
# Run the gnome without remembering anything.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$HERE/.venv-gnomo/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
PYTHONPATH="$HERE/logic-probe" exec "$PY" -m gnomo "$@"
SHIM
chmod +x "$REPO_DIR/gnomo"

# --- 6. go -----------------------------------------------------------------
say "Running the walkthrough"
set +e
PYTHONPATH="$REPO_DIR/logic-probe" "$PY" -m gnomo setup mcu --fix
rc=$?
set -e

say "From now on, just run:"
note "cd $REPO_DIR && ./gnomo setup mcu"
note "cd $REPO_DIR && ./gnomo next"
exit $rc
