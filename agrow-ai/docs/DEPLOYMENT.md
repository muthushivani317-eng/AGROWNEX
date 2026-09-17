# 🚀 AGROWAI DEPLOYMENT GUIDE

Version: Foundation Release (V1)

---

# PURPOSE

This document defines how AgrowAI is developed, tested, deployed, monitored and scaled.

The deployment architecture should support:

• Mobile App
• Admin Dashboard
• Future Buyer Portal
• Future FPO Portal

The system must be production-ready, secure and scalable.

---

# ENVIRONMENTS

Development

↓

Testing

↓

Staging

↓

Production

Each environment has its own

Database

Redis

Storage

Secrets

Configuration

Logging

---

# TECH STACK

Frontend

React Native (Expo)

Backend

FastAPI

Database

PostgreSQL + PostGIS

Cache

Redis

Storage

AWS S3

Container

Docker

Reverse Proxy

NGINX

Cloud

AWS

Monitoring

Prometheus

Grafana

Logging

Loki

Git

GitHub

CI/CD

GitHub Actions

---

# INFRASTRUCTURE

                Internet

                    │

                    ▼

             AWS Load Balancer

                    │

         ┌──────────┴───────────┐

         ▼                      ▼

   FastAPI Instance       FastAPI Instance

         │

         ▼

      PostgreSQL

         │

         ▼

        Redis

         │

         ▼

       AWS S3

         │

         ▼

    AI Router

     │      │

     ▼      ▼

ChatGPT   Gemini

---

# LOCAL DEVELOPMENT

Requirements

Python 3.12+

Node.js LTS

Expo CLI

Docker Desktop

Git

VS Code

Claude Code

---

# LOCAL SERVICES

Docker Compose

Starts

PostgreSQL

Redis

MinIO (optional local S3)

FastAPI

Admin

---

# GIT BRANCHES

main

Production

develop

Development

feature/*

New Features

bugfix/*

Bug Fixes

hotfix/*

Production Fixes

---

# CI PIPELINE

Every Pull Request

↓

Lint

↓

Type Check

↓

Unit Tests

↓

Integration Tests

↓

Security Scan

↓

Docker Build

↓

Deploy to Staging

---

# CD PIPELINE

Merge to Main

↓

Production Build

↓

Docker Image

↓

Push Registry

↓

Deploy

↓

Health Check

↓

Smoke Test

↓

Notify Team

---

# DATABASE MIGRATIONS

Alembic

Every deployment

↓

Run migrations

↓

Verify

↓

Deploy

Never manually edit production database.

---

# STORAGE

AWS S3 Buckets

profile-images/

farm-images/

disease-images/

growth-images/

produce-images/

documents/

voice/

---

# CACHE

Redis

Weather

Market Prices

Schemes

AI Memory Cache

Sessions

Notification Queue

---

# BACKGROUND WORKERS

Celery

Jobs

Weather Sync

Market Sync

Notification Delivery

Image Processing

Growth Analysis

AI Cleanup

---

# LOGGING

API Logs

Error Logs

AI Logs

Notification Logs

Authentication Logs

Audit Logs

---

# MONITORING

Prometheus

Grafana

Health Endpoints

Request Count

Response Time

CPU

RAM

Disk

Database

Redis

---

# ALERTS

API Down

Database Down

Redis Down

AI Failure

Upload Failure

High CPU

Low Disk

---

# BACKUP

Database

Daily

Incremental

Point-in-Time Recovery

S3

Versioning Enabled

Cross-region backup

---

# SCALING

Horizontal

FastAPI

Vertical

Database

Redis Cluster

CDN

CloudFront

Image Optimization

Auto Scaling

---

# RELEASE STRATEGY

Development

↓

Testing

↓

Internal Farmers

↓

Pilot Villages

↓

Thoothukudi Launch

↓

Tamil Nadu

↓

South India

↓

India

---

# DISASTER RECOVERY

Failure

↓

Automatic Detection

↓

Rollback

↓

Restore Backup

↓

Health Verification

↓

Resume Service

---

# PRODUCTION CHECKLIST

✓ HTTPS

✓ Environment Variables

✓ Secrets Manager

✓ Backups

✓ Monitoring

✓ Logging

✓ Rate Limiting

✓ Health Checks

✓ Docker

✓ CI/CD

✓ Auto Rollback

✓ S3 Versioning

✓ Database Migration

✓ Performance Testing

✓ Security Scan

---

# FUTURE DEPLOYMENTS

Admin Dashboard

FPO Dashboard

Buyer Portal

Satellite AI

Drone AI

IoT Gateway

Voice Assistant

All use the same backend.
