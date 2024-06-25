#!/bin/sh

# Ensure the data directory exists
mkdir -p /app/data

# Ensure the log file exists and set the correct permissions
touch /app/data/message_logs.ndjson
chmod 666 /app/data/message_logs.ndjson

# Run the bot as appuser
exec python bot.py
