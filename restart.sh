#!/bin/bash

# Restart the Book Translation Tool application
# This script kills any existing process on port 5001 and starts the app in background mode

echo "Restarting Book Translation Tool..."

# Kill any existing Flask process on port 5001
echo "Stopping existing processes on port 5001..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true

# Wait for port to be free
sleep 2

# Start the application in background
echo "Starting application..."
./start_uv_bg.sh

# Check if start was successful
if [ $? -eq 0 ]; then
    echo "Application restarted successfully!"
    echo "Access the application at: http://localhost:5001"
    echo "Access admin interface at: http://localhost:5001/admin"
else
    echo "Failed to restart application. Check logs for details."
    exit 1
fi
