#!/usr/bin/env bash
SCRIPT_PATH="$1"
TARGET="$2"

# very simple runner: run python script with timeout and print stdout
timeout ${RUNNER_TIMEOUT:-30}s python3 "$SCRIPT_PATH"
