#!/usr/bin/env bash
# Launch Chrome with remote debugging so the app can attach for Record (course fetch).
# 1. Quit any running Chrome, then run this script (from project root).
# 2. Use Record in the app; it will connect to this Chrome (your profile, already logged in).
#
# For a non-Default profile (e.g. Profile 1): run with env var set, e.g.
#   CHROME_PROFILE_DIRECTORY="Profile 1" ./scripts/launch-chrome-for-record.sh

set -e
CHROME="${CHROME_EXECUTABLE:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
USER_DATA_DIR="${CHROME_USER_DATA_DIR:-$HOME/Library/Application Support/Google/Chrome}"
PROFILE="${CHROME_PROFILE_DIRECTORY:-Default}"
exec "$CHROME" --remote-debugging-port=9222 --user-data-dir="$USER_DATA_DIR" --profile-directory="$PROFILE"
