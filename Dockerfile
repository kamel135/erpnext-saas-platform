FROM node:18-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    docker-cli \
    bash

# Copy package files
COPY platform/package*.json ./

# Install Node dependencies
RUN npm install

# Copy application
COPY platform/ .
COPY templates/ ./templates/

# Expose port
EXPOSE 3000

# Start application
CMD ["npm", "start"]
