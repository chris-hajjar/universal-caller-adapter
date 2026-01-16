#!/bin/bash

# Simple Demo Runner for Universal Caller Adapter
# This script starts the server and runs the simple, educational demo

set -e

echo "=========================================="
echo "  Universal Adapter - Simple Demo"
echo "=========================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
fi

# Start the server in the background
echo "Starting server..."
python main.py &
SERVER_PID=$!

# Give the server time to start
echo "Waiting for server to start..."
sleep 3

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ERROR: Server failed to start"
    exit 1
fi

echo "Server is running (PID: $SERVER_PID)"
echo ""

# Run the simple demo
echo "Running simple demo..."
echo ""
python simple_demo.py

# Cleanup
echo ""
echo "Shutting down server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Demo complete!"
echo "=========================================="
