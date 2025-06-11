#!/bin/bash

echo "🚀 Quick Start ERPNext SaaS Platform"
echo "===================================="

# Stop any running containers
docker compose down -v

# Build fresh
echo "🔨 Building images..."
docker compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker compose up -d

# Wait for DB to be ready
echo "⏳ Waiting for database..."
sleep 10

# Create database manually if needed
echo "📊 Setting up database..."
docker compose exec platform-db createdb -U saas_admin saas_platform 2>/dev/null || true

# Initialize database
./scripts/init-db.sh

# Show logs
echo "📋 Service Status:"
docker compose ps

echo "✅ Done! Access the platform at http://localhost:3000"
echo "📜 To see logs: docker compose logs -f"
