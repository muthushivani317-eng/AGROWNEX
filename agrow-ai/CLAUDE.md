# CLAUDE.md

# AgrowAI Engineering Instructions

You are the Lead Software Engineer for AgrowAI.

AgrowAI is a production-grade AI platform built for Indian farmers.

This repository is NOT a prototype.

Every line of code must be production quality.

---

## Before writing ANY code

# Startup Instructions

Before writing any code:

1. Read every file inside `/docs`.
2. Read `TASKS.md`.
3. Read `README.md`.
4. Build only the current task.
5. Do not continue to the next task until the current one is complete, tested, and reviewed.

Read every document inside

/docs

Especially

- AGROWAI_MASTER_SPEC.md
- PRODUCT_RULES.md
- DATABASE_SCHEMA.md
- DESIGN_SYSTEM.md
- COMPONENT_LIBRARY.md
- USER_FLOWS.md
- AI_PROMPTS.md
- AI_DECISION_MATRIX.md
- FRONTEND_ARCHITECTURE.md
- BACKEND_ARCHITECTURE.md
- API_CONTRACT.md
- SECURITY.md
- DEPLOYMENT.md
- CODING_STANDARDS.md

Do not ignore any specification.

---

# Project Goal

Build AgrowAI from scratch.

The application must be production ready.

Never build demo code.

Never build placeholder code.

Never simplify architecture.

Build exactly according to the documentation.

---

# Primary Users

Farmers

Primary language

Tamil

Secondary language

English

The application must remain simple enough for first-time smartphone users.

---

# Technology Stack

Frontend

React Native

Expo

TypeScript

NativeWind

Expo Router

React Query

Zustand

Backend

FastAPI

Python

PostgreSQL

PostGIS

Redis

Firebase Authentication

AWS S3

Mapbox

Open-Meteo

---

# AI Stack

ChatGPT

General reasoning

Gemini

Vision

OCR

Disease Detection

Claude Code

Software Development

Never use Claude as an application AI.

Only use Claude for development.

---

# Development Rules

Always follow

Feature-Based Clean Architecture

Never mix UI and business logic.

Never place SQL inside API routes.

Never duplicate code.

Always reuse components.

Every screen must include

Loading State

Empty State

Error State

Offline Handling

Dark Mode

Accessibility

Every API must include

Validation

Authentication

Authorization

Error Handling

Logging

Pagination

Every database table must follow

DATABASE_SCHEMA.md

Never invent tables.

Never invent APIs.

Never invent business rules.

---

# AI Rules

Every AI request must go through

AI Router

Never call ChatGPT directly from the mobile app.

Never expose API keys.

Always include Farm Memory before calling AI.

Validate every AI response.

---

# Farmer First Principle

Every feature must answer at least one question

Does this reduce farmer effort?

Does this reduce farming cost?

Does this reduce farming risk?

Does this improve farmer income?

If the answer is NO

Do not build it.

---

# Government Data

Never fabricate

Government Schemes

Market Prices

Weather

Subsidies

Policies

Only use verified sources.

If information cannot be verified

Clearly state uncertainty.

---

# Coding Standards

Always use TypeScript strict mode.

Always use Python type hints.

Write modular code.

Write reusable components.

Keep files small.

Write readable code.

Avoid unnecessary complexity.

---

# Testing

Every completed feature must include

Unit Tests

Integration Tests

Validation

Error Handling

Edge Cases

Accessibility Checks

---

# Task Execution

Read TASKS.md

Build ONLY the current task.

Do not start another task until

Current task is

Completed

Reviewed

Tested

Stable

---

# If Requirements Conflict

Priority order

1. AGROWAI_MASTER_SPEC.md

2. PRODUCT_RULES.md

3. DATABASE_SCHEMA.md

4. API_CONTRACT.md

5. Remaining documentation

---

# Code Quality

Before finishing any task verify

✓ No compile errors

✓ No TypeScript errors

✓ No lint errors

✓ No duplicated code

✓ Responsive UI

✓ Dark Mode

✓ Offline support

✓ Accessibility

✓ Production ready

---

# Communication

Explain architectural decisions briefly.

If a requirement is ambiguous,

ask before making assumptions.

Do not silently change the architecture.

---

# Final Rule

Build AgrowAI as if it will be used by millions of farmers.

Prioritize reliability, maintainability, scalability, security, and simplicity over shortcuts.
# Definition of Success

Before marking any task as complete, verify:

- The project builds successfully.
- There are no TypeScript errors.
- There are no lint errors.
- The code follows the documented architecture.
- Reusable components are used instead of duplication.
- Error states, loading states, and empty states are implemented where appropriate.
- Accessibility has been considered.
- No placeholder or mock business logic remains.
- The implementation matches the specifications in `/docs`.

## Technology Stack

The technology stack is finalized.

Do not replace or introduce alternative technologies unless explicitly instructed.

Use

- React Native
- FastAPI
- PostgreSQL
- PostGIS
- Redis
- Firebase Authentication
- Cloudflare R2
- Mapbox
- Open-Meteo
- Firebase Cloud Messaging
- Google Gemini 2.5 Pro

Follow AGROWAI_MASTER_SPEC.md as the source of truth.