#!/bin/bash
# LaunchAgent wrapper: keep Gnomo alive. `open -W` blocks until the app quits,
# then returns; the agent loops, so a quit or crash is followed by a relaunch.
APP="/Users/christian.grau/workspace/gnomo/companion/build/Gnomo.app"
while true; do
  /usr/bin/open -W "$APP"
  sleep 5
done
