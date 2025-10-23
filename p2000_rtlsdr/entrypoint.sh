#!/bin/bash

# Start the main app in the background
/p2000.py &

# Start the watchdog in the foreground to keep the container running
/watchdog.sh
