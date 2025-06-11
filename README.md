# ERPNext Multi-Tenant SaaS Platform

<div align="center">
  <img src="https://img.shields.io/badge/ERPNext-v15-blue.svg" alt="ERPNext Version">
  <img src="https://img.shields.io/badge/Docker-Compose-brightgreen.svg" alt="Docker Compose">
  <img src="https://img.shields.io/badge/Node.js-18+-green.svg" alt="Node.js">
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</div>

## 🌟 نظرة عامة

منصة SaaS متعددة المستأجرين لـ ERPNext تتيح إنشاء وإدارة مثيلات ERPNext منفصلة لكل عميل مع عزل كامل وإدارة متقدمة للموارد.

### لقطات الشاشة
![Dashboard](docs/images/dashboard.png)
*لوحة التحكم الرئيسية*

## ✨ المميزات

- 🏢 **Multi-Tenancy**: عزل كامل لكل عميل في Docker container منفصل
- 🚀 **إنشاء سريع**: إنشاء مثيل ERPNext جديد في دقائق
- 📊 **مراقبة الموارد**: مراقبة CPU والذاكرة في الوقت الفعلي
- 💳 **نظام الفوترة**: خطط مرنة (Starter, Professional, Enterprise)
- 🔒 **الأمان**: عزل كامل وSSL لكل عميل
- 🎨 **واجهة سهلة**: لوحة تحكم عربية سهلة الاستخدام
- 📱 **متجاوب**: يعمل على جميع الأجهزة
- 🔄 **نسخ احتياطي**: نسخ احتياطي تلقائي يومي

## 🛠️ التقنيات المستخدمة

### Backend
- Node.js 18 + Express.js
- PostgreSQL 15
- Redis 7
- Docker & Docker Compose

### Frontend
- EJS Templates
- Bootstrap 5
- Vanilla JavaScript

### Infrastructure
- Nginx (Reverse Proxy)
- Docker Containers
- Shell Scripts

## 📋 المتطلبات

- Docker Engine 20.10+
