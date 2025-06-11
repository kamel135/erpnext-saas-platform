#!/bin/bash

set -e

echo "🚀 ERPNext SaaS Platform Setup"
echo "=============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check prerequisites
echo -e "\n${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites installed${NC}"

# Create .env if not exists
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}🔐 Creating .env file...${NC}"
    cp .env.example .env
    
    # Generate secure passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SESSION_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    # Update .env with generated values
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your_secure_password_here/$DB_PASSWORD/" .env
        sed -i '' "s/generate-a-secure-random-string/$SESSION_SECRET/" .env
    else
        # Linux
        sed -i "s/your_secure_password_here/$DB_PASSWORD/" .env
        sed -i "s/generate-a-secure-random-string/$SESSION_SECRET/" .env
    fi
    
    echo -e "${GREEN}✅ .env file created with secure passwords${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}📁 Creating directories...${NC}"
mkdir -p tenants logs backups nginx/sites

# Set permissions
chmod +x scripts/*.sh

# Build and start services
echo -e "\n${YELLOW}🔨 Building Docker images...${NC}"
docker compose build

echo -e "\n${YELLOW}🚀 Starting services...${NC}"
docker compose up -d

# Wait for services to be ready
echo -e "\n${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Initialize database
echo -e "\n${YELLOW}🗄️ Initializing database...${NC}"
./scripts/init-db.sh

# Show status
echo -e "\n${YELLOW}📊 Service Status:${NC}"
docker compose ps

echo -e "\n${GREEN}✅ Setup completed successfully!${NC}"
echo -e "\n📌 Access the platform at: ${YELLOW}http://localhost:3000${NC}"
echo -e "📌 Platform API: ${YELLOW}http://localhost:3000/api${NC}"
echo -e "\n💡 To create your first tenant, use the web interface or run:"
echo -e "   ${YELLOW}./scripts/create_tenant.sh \"Company Name\" \"subdomain\" \"email@example.com\" \"plan\"${NC}"
echo -e "\n📖 For more information, check the README.md file"
