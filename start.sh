#!/bin/bash
# Start script for unified container on Render

# Render assigns PORT dynamically (usually 10000)
export PORT=${PORT:-3000}
export API_PORT=8000

echo "========================================="
echo "Starting AIOS Platform..."
echo "========================================="
echo "Frontend (Next.js) will bind to: 0.0.0.0:$PORT"
echo "Backend (FastAPI) will run on: localhost:$API_PORT"
echo "========================================="

# Start backend API in background
echo "[1/2] Starting FastAPI backend..."
cd /app
uvicorn engine_api.main:app --host 127.0.0.1 --port $API_PORT --log-level info &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:$API_PORT/coins > /dev/null 2>&1; then
        echo "✓ Backend is ready (PID: $BACKEND_PID)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Backend failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start frontend on Render's PORT
echo "[2/2] Starting Next.js frontend..."
cd /app/frontend

# Next.js standalone needs these env vars
export HOSTNAME="0.0.0.0"
export NEXT_PUBLIC_API_URL="/api"

# Start Next.js - it will use PORT env var
node server.js &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:$PORT > /dev/null 2>&1; then
        echo "✓ Frontend is ready (PID: $FRONTEND_PID)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Frontend failed to start within 30 seconds"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

echo "========================================="
echo "✓ AIOS Platform is LIVE!"
echo "========================================="
echo "Access URL: Check Render dashboard for your deployment URL"
echo "Health check: http://localhost:$PORT"
echo "========================================="

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID

# If one exits, kill the other and exit
echo "A service has stopped. Shutting down..."
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
exit $?
