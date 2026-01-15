#!/bin/bash

# Team Assistant - Quick Demo Script

echo "🚀 Team Assistant - Quick Demo"
echo "================================"
echo ""

# Check if JAR exists
if [ ! -f "backend/build/libs/project-assistant-1.0.0.jar" ]; then
    echo "❌ JAR not found. Building..."
    ./gradlew clean build shadowJar
    echo ""
fi

# Check cache
if [ ! -f ".team-assistant/cache.json" ]; then
    echo "⚠️  Cache not found. Creating demo data..."
    mkdir -p .team-assistant
    # Demo data already exists, just mention it
fi

# Start server
echo "🔥 Starting Team Assistant server..."
echo ""
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant &
SERVER_PID=$!
echo "Server started (PID: $SERVER_PID)"
echo ""

# Wait for server to start
sleep 5

# Test API
echo "📡 Testing API endpoints..."
echo ""
echo "1. Health Check:"
curl -s http://localhost:8080/health | jq '.'
echo ""

echo "2. Configuration:"
curl -s http://localhost:8080/api/config | jq '{github, scoring}'
echo ""

echo "3. Top 3 Issues (by priority):"
curl -s http://localhost:8080/api/issues | jq '.[:3] | .[] | {
  number: .issue.number,
  title: .issue.title,
  priority: .priorityScore,
  commits: .commitCount
}'
echo ""

echo "4. Cache Stats:"
curl -s http://localhost:8080/api/cache/stats | jq '.'
echo ""

echo "✅ Demo complete! Server is running at http://localhost:8080"
echo ""
echo "Available commands:"
echo "  curl http://localhost:8080/api/issues              # Get all issues"
echo "  curl http://localhost:8080/api/issues/1            # Get issue details"
echo "  curl -X POST http://localhost:8080/api/issues/cache/refresh  # Refresh cache"
echo ""
echo "Press Ctrl+C to stop the server"

# Wait for Ctrl+C
wait $SERVER_PID
