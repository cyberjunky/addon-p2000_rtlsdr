#!/bin/bash

LOG_PATTERN="rtlsdr_read_reg failed"
ADDON_RESTART_URL="http://supervisor/addons/self/restart"
AUTH_HEADER="Authorization: Bearer $SUPERVISOR_TOKEN"

# Monitor the container's stdout log (fd 1)
# You can also adapt this if your app logs to a file instead

tail -F /proc/1/fd/1 | while read -r line
do
  echo "$line" | grep -q "$LOG_PATTERN"
  if [ $? -eq 0 ]; then
    echo "Error pattern detected, restarting addon..."
    curl -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" "$ADDON_RESTART_URL"
    # Optionally add delay or exit here to avoid rapid restarts
    sleep 30
  fi
done
