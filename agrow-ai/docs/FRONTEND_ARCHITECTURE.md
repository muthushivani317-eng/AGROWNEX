# 📱 AGROWAI FRONTEND ARCHITECTURE

Version: Foundation Release (V1)

---

# PURPOSE

This document defines the complete frontend architecture for AgrowAI.

The frontend must be:

• Modular
• Scalable
• Offline-first
• AI-ready
• Tamil-first
• Production-ready

The frontend should support millions of farmers without requiring major architectural changes.

---

# TECHNOLOGY STACK

Framework

React Native

Platform

Expo SDK Latest

Language

TypeScript

Navigation

Expo Router

Styling

NativeWind

State Management

Zustand

Server State

TanStack Query

Forms

React Hook Form

Validation

Zod

Animation

React Native Reanimated

Gesture

Gesture Handler

Bottom Sheet

Gorhom Bottom Sheet

Maps

Mapbox

Camera

Expo Camera

Image Picker

Expo Image Picker

Notifications

Firebase Cloud Messaging

Storage

MMKV

Offline Database

SQLite

Localization

i18next

---

# APPLICATION STRUCTURE

app/

components/

features/

hooks/

services/

stores/

types/

utils/

constants/

assets/

theme/

providers/

navigation/

localization/

lib/

config/

---

# FEATURE STRUCTURE

Every feature follows

feature/

components/

screens/

hooks/

services/

types/

store/

api/

utils/

constants/

Example

features/

disease/

components/

screens/

hooks/

services/

store/

api/

types/

utils/

---

# NAVIGATION

Bottom Navigation

🏠 Home

🤖 AI

🌱 Farm

📈 Market

👤 Profile

Additional screens use Stack Navigation.

---

# HOME SCREEN

Display

Greeting

Weather

Farm Health

Today's Tasks

AI Recommendations

Crop Growth

Market Prices

Government Schemes

Notifications

Sell Produce

---

# STATE MANAGEMENT

Global State

Authentication

Language

Theme

Farmer Profile

Current Farm

Notifications

Server State

Weather

Market Prices

Government Schemes

AI Conversations

Disease History

Growth Reports

Use TanStack Query.

Never store server data inside Zustand.

---

# LOCAL STORAGE

Store

JWT

Farmer Profile

Current Farm

Language

Theme

Offline Queue

Recent AI History

---

# OFFLINE STRATEGY

If internet unavailable

↓

Store Request

↓

Offline Queue

↓

Sync Automatically

Support

Farm Registration

Crop Growth Upload

AI Chat Queue

Produce Listing Draft

Profile Update

---

# COMPONENT LIBRARY

Common Components

AgButton

AgCard

AgInput

AgDropdown

AgAvatar

AgModal

AgBottomSheet

AgTimeline

AgWeatherCard

AgMarketCard

AgNotificationCard

AgGrowthCard

AgProduceCard

AgSchemeCard

AgCamera

AgVoiceRecorder

AgSkeleton

AgEmptyState

AgErrorState

---

# HOOKS

useAuth()

useWeather()

useDisease()

useAI()

useGrowth()

useMarket()

useGovernmentSchemes()

useNotifications()

useOffline()

usePermissions()

---

# SERVICES

Auth Service

Weather Service

Disease Service

AI Service

Growth Service

Market Service

Produce Service

Government Scheme Service

Notification Service

Upload Service

---

# API LAYER

Every request

↓

API Client

↓

Interceptor

↓

Authentication

↓

Retry

↓

Logging

↓

Response

Never call fetch() directly inside screens.

---

# IMAGE PIPELINE

Camera

↓

Compression

↓

Thumbnail

↓

Upload

↓

S3

↓

Database

Support

Disease Images

Growth Images

Produce Images

Profile Images

---

# VOICE PIPELINE

Tamil Speech

↓

Speech To Text

↓

ChatGPT

↓

Tamil Response

↓

Text To Speech

↓

Farmer

---

# AI CHAT

Features

Streaming

Typing Indicator

Voice

Camera

Gallery

Markdown

Suggestions

Conversation History

---

# LOCALIZATION

Default

Tamil

Secondary

English

Every screen must support

Text

Dates

Numbers

Units

---

# THEMES

Light

Dark

Auto

Use Design System colors.

---

# PERFORMANCE

Lazy Loading

Image Caching

Memoization

Virtualized Lists

Code Splitting

Optimized Rendering

---

# ACCESSIBILITY

Large Fonts

48dp Touch Targets

Voice Support

Screen Reader

High Contrast

---

# TESTING

Unit Tests

Component Tests

Navigation Tests

Offline Tests

Performance Tests

Accessibility Tests

---

# FUTURE SUPPORT

Tablet Layout

Foldable Devices

Desktop Web

Wearables

Voice Assistant

IoT Dashboard

Satellite Dashboard
