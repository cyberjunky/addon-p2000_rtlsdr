#!/bin/bash

LOG_PATTERN="cb transfer status: 5, canceling..."
ADDON_RESTART_URL="http://supervisor/addons/self/restart"
AUTH_HEADER="Authorization: Bearer $SUPERVISOR_TOKEN"

# Monitor the container's stdout log (fd 1) and stderr (fd 2)

tail -F /proc/1/fd/1 /proc/1/fd/2 | while read -r line
do
  echo "$line" | grep -q "$LOG_PATTERN"
  if [ $? -eq 0 ]; then
    echo "Error pattern detected, restarting addon..."
    curl -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" "$ADDON_RESTART_URL"
    # Optionally add delay or exit here to avoid rapid restarts
    sleep 30
  fi
done
