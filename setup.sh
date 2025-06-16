#!/bin/bash

echo "🚀 Setting up ERPNext SaaS Platform..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p saas_sites
mkdir -p logs

# Set permissions
echo "🔒 Setting permissions..."
sudo chown -R $USER:$USER saas_sites logs

# Copy env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your settings"
fi

# Add hosts entry
echo "🌐 Adding hosts entry..."
if ! grep -q "manage.orbscope.local" /etc/hosts; then
    echo "127.0.0.1 manage.orbscope.local" | sudo tee -a /etc/hosts
fi

echo "✅ Setup complete! Run 'docker compose up -d' to start the platform."
