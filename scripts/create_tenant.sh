#!/bin/bash

# معاملات السكريبت
TENANT_NAME=$1
TENANT_SUBDOMAIN=$2
TENANT_EMAIL=$3
TENANT_PLAN=${4:-starter}

# توليد معرف فريد
TENANT_ID=$(uuidgen | cut -d'-' -f1)
TENANT_DB_PASSWORD=$(openssl rand -base64 12)
TENANT_PORT=$((8000 + RANDOM % 1000))

echo "🚀 Creating new tenant..."
echo "   Name: $TENANT_NAME"
echo "   Subdomain: $TENANT_SUBDOMAIN"
echo "   ID: $TENANT_ID"

# إنشاء مجلد للـ tenant
mkdir -p tenants/$TENANT_ID

# نسخ وتعديل template
cp templates/erpnext-template.yaml tenants/$TENANT_ID/docker-compose.yml

# استبدال المتغيرات
sed -i "s/{{TENANT_ID}}/$TENANT_ID/g" tenants/$TENANT_ID/docker-compose.yml
sed -i "s/{{TENANT_SUBDOMAIN}}/$TENANT_SUBDOMAIN/g" tenants/$TENANT_ID/docker-compose.yml
sed -i "s/{{TENANT_DB_PASSWORD}}/$TENANT_DB_PASSWORD/g" tenants/$TENANT_ID/docker-compose.yml
sed -i "s/{{TENANT_PORT}}/$TENANT_PORT/g" tenants/$TENANT_ID/docker-compose.yml

# تشغيل ERPNext للـ tenant
cd tenants/$TENANT_ID
docker-compose up -d

echo "✅ Tenant created successfully!"
echo "   URL: http://$TENANT_SUBDOMAIN.localhost:$TENANT_PORT"
