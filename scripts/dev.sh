#!/bin/bash
# Start both backend and frontend for development

set -e

# Kill background jobs on exit
trap 'kill 0' EXIT

echo "Starting New Business Locator development servers..."
echo ""

# Start FastAPI backend
echo "[Backend] Starting uvicorn on port 8000..."
uvicorn api.main:app --reload --port 8000 &

# Wait for backend to start
sleep 2

# Start Next.js frontend
echo "[Frontend] Starting Next.js on port 3000..."
cd frontend && npm run dev &

echo ""
echo "=========================================="
echo "  Dashboard: http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for all background jobs
wait
