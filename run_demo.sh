#!/bin/bash

# Run server and demo together

set -e

echo "Starting Universal Caller Adapter demo..."
echo ""

# Activate venv
source venv/bin/activate

# Start server in background
echo "Starting server..."
python main.py > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to be ready..."
sleep 3

# Run demo
echo ""
python demo.py

# Cleanup
echo ""
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo "Demo complete!"
