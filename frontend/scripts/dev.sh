#!/bin/bash

# Start both API and frontend development servers

set -e

echo "Starting New Business Locator development servers..."
echo

# Start backend in background
echo "[Backend] Starting uvicorn on port 8000..."
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Give backend time to start
sleep 2

# Start frontend in background
echo "[Frontend] Starting Next.js on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Print access URLs
echo
echo "=========================================="
echo "  Dashboard: http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "=========================================="
echo
echo "Press Ctrl+C to stop all servers"

# Trap Ctrl+C and kill both processes
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for both processes
wait
