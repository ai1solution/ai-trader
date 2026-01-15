#!/bin/bash
# Start script for unified container

# Use PORT from environment or default to 3000
export PORT=${PORT:-3000}
export API_PORT=8000

echo "Starting AI Trader Platform..."
echo "Frontend will run on port: $PORT"
echo "Backend will run on port: $API_PORT"

# Start backend API in background
echo "Starting backend API..."
cd /app
uvicorn engine_api.main:app --host 0.0.0.0 --port $API_PORT &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start"
    exit 1
fi

echo "Backend started successfully (PID: $BACKEND_PID)"

# Start frontend
echo "Starting frontend..."
cd /app/frontend
export HOSTNAME="0.0.0.0"
export NEXT_PUBLIC_API_URL="http://localhost:$API_PORT"
node server.js &
FRONTEND_PID=$!

# Wait for frontend to be ready
sleep 5

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "Frontend failed to start"
    kill $BACKEND_PID
    exit 1
fi

echo "Frontend started successfully (PID: $FRONTEND_PID)"
echo "Platform is ready!"
echo "Access the dashboard at: http://localhost:$PORT"

# Wait for both processes
wait -n $BACKEND_PID $FRONTEND_PID

# Exit with status of first process to exit
exit $?
