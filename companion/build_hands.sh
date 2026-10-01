#!/bin/sh
# Build GNOMO's hands helper (macOS only). Output: companion/build/gnomo-hands
# First use: macOS asks you to allow it under Privacy & Security > Accessibility.
set -eu
cd "$(dirname "$0")"
mkdir -p build
swiftc -O gnomo_hands.swift -o build/gnomo-hands
echo "built companion/build/gnomo-hands"
