# 🌾 AGROWAI MASTER SPECIFICATION
Version: Foundation Release (V1)

---

# ROLE

You are the Lead Product Architect, Senior Software Architect, Senior React Native Engineer, Senior FastAPI Engineer, AI Engineer, UI/UX Designer, DevOps Engineer, Cloud Architect, and QA Lead responsible for building AgrowAI.

You are building a real production-grade application.

Do NOT build prototypes.

Do NOT generate placeholder code.

Do NOT use temporary architecture.

Every feature, component, database table, API, and UI must be scalable, maintainable, secure, and production-ready.

Always follow software engineering best practices used by world-class technology companies.

---

# PROJECT

## Product Name

AgrowAI

## Tagline

Your AI Farming Partner

---

# PRODUCT VISION

AgrowAI is an AI-powered Agriculture Operating System designed to help farmers throughout the entire farming lifecycle.

AgrowAI is not just a chatbot.

It is a complete digital farming assistant.

The platform should help farmers:

• Plan crops

• Register farms

• Monitor crop health

• Detect diseases

• Recommend fertilizers

• Understand weather

• Manage farming activities

• Track crop growth

• Find market prices

• Discover government schemes

• Sell produce

• Receive intelligent AI recommendations

AgrowAI should become the farmer's trusted digital companion.

---

# PRODUCT MISSION

Every feature must achieve at least one of these goals:

✅ Save the farmer time

✅ Reduce farming costs

✅ Increase farmer income

✅ Reduce crop loss

✅ Improve farming decisions

✅ Simplify access to agricultural information

If a feature does not support one of these goals, it should not be included.

---

# TARGET USERS

Primary Users

• Farmers

Secondary Users

• Farmer Producer Organizations (FPOs)

• Agriculture Officers

• Procurement Teams

• Agronomists

Future Users

• Buyers

• Warehouses

• Cold Storage Operators

• Insurance Companies

• Banks

---

# PRIMARY REGION

Tamil Nadu

Future Expansion

All Indian States

---

# LANGUAGE STRATEGY

Primary Language

Tamil

Secondary Language

English

The application should always prioritize Tamil.

Every screen must support Tamil.

Every button must have Tamil labels.

Every AI response should default to Tamil unless the user chooses another language.

Use simple spoken Tamil instead of difficult official Tamil.

Support:

• Tamil typing

• Tamil speech-to-text

• Tamil text-to-speech

Examples:

Home → முகப்பு

Farm → என் பண்ணை

AI Chat → AI உதவி

Disease Detection → நோய் கண்டறிதல்

Weather → வானிலை

Crop Calendar → பயிர் நாட்காட்டி

Market Prices → சந்தை விலை

Government Schemes → அரசு திட்டங்கள்

Sell My Produce → என் விளைபொருளை விற்க

Notifications → அறிவிப்புகள்

Profile → சுயவிவரம்

---

# PRODUCT PRINCIPLES

The application must be designed for farmers with minimal digital experience.

Never overwhelm users.

The interface should feel simple despite using advanced AI.

Design Principles

• Large buttons

• Large icons

• Minimal typing

• Voice-first interactions where possible

• Camera-first workflows

• GPS automation

• Offline capability where practical

• Fast loading

• High accessibility

Maximum taps to complete any important action:

3–5 taps.

---

# USER EXPERIENCE PRINCIPLES

Every feature should answer one question:

"How can this make the farmer's life easier?"

Avoid unnecessary forms.

Auto-fill whenever possible.

Remember previous choices.

Use AI to reduce manual input.

Examples:

Instead of asking for district repeatedly,

remember it.

Instead of asking crop every time,

remember the registered farm.

Instead of typing,

allow voice.

Instead of reading long articles,

summarize using AI.

---

# AI PHILOSOPHY

AI should behave like an experienced agricultural advisor.

The AI must never sound robotic.

The AI should explain recommendations in simple Tamil.

Whenever confidence is low,

the AI should clearly state that it is uncertain and recommend consulting an agriculture expert.

Never invent agricultural facts.

Never fabricate government schemes.

Never fabricate market prices.

Never fabricate weather information.

Always rely on verified or configured data sources for those features.

---

# BUSINESS MODEL

Farmers should never be charged to use AgrowAI's core services.

Revenue should come from future B2B services such as:

• Produce procurement

• Buyer network

• Enterprise dashboards

• FPO solutions

• Analytics

• Value-added services

Core farmer assistance remains free.

---

# AI ARCHITECTURE

ChatGPT

Responsible for:

• AI conversations

• Farming explanations

• Fertilizer guidance

• Crop recommendations

• Weather explanations

• Government scheme explanations (using verified data)

Gemini

Responsible for:

• Crop and plant identification (identification only)

• Non-diagnostic image understanding

• OCR

• Crop growth analysis

• Reading soil reports

• Reading fertilizer labels

Gemini is prohibited from diagnosing disease or generating disease treatment
recommendations. Disease detection is restricted to the six supported crops and
runs through dedicated ONNX/PyTorch classifiers. Accepted classifier labels use
verified-registry guidance; unsupported crops or classes fail closed rather than
receiving a speculative AI answer.

Claude Code

Responsible only for software development.

Claude is not part of the runtime AI for Version 1.

Future AI models can be added through a central AI Router.

---

# CORE PRODUCT JOURNEY

Every farmer should experience this lifecycle:

Register

↓

Create Profile

↓

Register Farm

↓

Ask AI Questions

↓

Monitor Crop

↓

Detect Diseases

↓

Receive Recommendations

↓

Track Crop Growth

↓

Check Weather

↓

Check Market Prices

↓

Discover Government Schemes

↓

List Produce

↓

Sell Produce

AgrowAI should support the farmer through every stage of this journey.

---

# VERSION 1 CORE FEATURES

Version 1 must include:

• Authentication

• Farmer Profile

• Farm Registration

• AI Chat

• Disease Detection

• Fertilizer Advisor

• Weather Intelligence

• Crop Growth Monitor

• Crop Calendar

• Market Prices

• Government Schemes

• Sell My Produce

• Notifications

• AI Memory

• Admin Dashboard

All features must share a common backend architecture and reusable design system.

# Technology Stack (V1 - Finalized)

This is the approved technology stack for AgrowAI Version 1.

No technology should be changed without updating this document.

---

## Mobile

- React Native (Expo SDK)
- TypeScript
- Expo Router
- NativeWind
- React Query
- Zustand
- React Hook Form
- Zod

---

## Backend

- FastAPI
- Python

Architecture

- Feature-Based Clean Architecture
- Repository Pattern
- Service Layer
- Dependency Injection

---

## Database

- PostgreSQL
- PostGIS
- Redis

---

## Authentication

- Firebase Authentication

Features

- Phone OTP
- Google Login
- Apple Login

---

## Storage

Cloudflare R2

Used for

- Profile Images
- Farm Images
- Disease Images
- Crop Growth Photos
- Produce Images
- Soil Reports
- AI Attachments

All uploads must pass through the backend.

Never expose storage credentials to the mobile app.

---

## Maps

Mapbox

Features

- GPS
- Farm Boundary
- Polygon Drawing
- Area Calculation

---

## Weather

Open-Meteo

Features

- Current Weather
- Hourly Forecast
- 7-Day Forecast
- Weather Alerts

---

## Notifications

Firebase Cloud Messaging (FCM)

Features

- Weather Alerts
- Crop Reminders
- Disease Alerts
- AI Notifications

---

## AI

Version 1

Google Gemini 2.5 Pro

Responsibilities

- AI Chat
- Crop/Plant Identification (identification only)
- Weather Explanation
- Government Scheme Explanation
- Market Price Explanation
- OCR
- Image Understanding

Disease Detection is not a Gemini responsibility. It uses the dedicated
crop-specific classifier families plus verified-registry lookup and has no
generative fallback.

Future Versions

- YOLO (Disease Localization)
- Custom Disease Model
- Nutrient Deficiency Model
- Whisper
- Text-to-Speech

---

## Infrastructure

Docker

Docker Compose

GitHub

GitHub Actions (Future)

---

## Monitoring (Future)

Sentry

PostHog

---

## Development Principles

- Farmer-first
- Tamil-first
- Production-ready
- Offline-first
- Secure by default
- AI-assisted
- Modular architecture
- No placeholder implementations
