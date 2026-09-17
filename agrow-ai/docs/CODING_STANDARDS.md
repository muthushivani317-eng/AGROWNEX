# 📘 AGROWAI CODING STANDARDS

Version: Foundation Release (V1)

---

# PURPOSE

This document defines mandatory engineering standards for AgrowAI.

Every generated file must follow these rules.

No exceptions.

---

# GENERAL PRINCIPLES

Write production-quality code.

Never generate placeholder code.

Never leave TODOs for critical functionality.

Prefer readability over cleverness.

Code should be maintainable for years.

Every feature must be modular.

Every feature must be testable.

Every feature must be documented.

---

# ARCHITECTURE

Follow

Feature-Based Clean Architecture

Every module contains

api/

service/

repository/

schemas/

models/

constants/

exceptions/

tests/

Never mix business logic with UI.

Never place SQL inside API routes.

Never access the database directly from controllers.

---

# FRONTEND

Language

TypeScript

Mode

Strict

Framework

React Native

Expo

Use

Functional Components

React Hooks

Never use Class Components.

---

# BACKEND

Language

Python

Framework

FastAPI

Always use

Type Hints

Pydantic

SQLAlchemy

Alembic

Async APIs where appropriate

---

# NAMING

Variables

camelCase

Functions

camelCase

React Components

PascalCase

Python Classes

PascalCase

Python Files

snake_case

Database Tables

snake_case

Database Columns

snake_case

Constants

UPPER_CASE

Enums

PascalCase

---

# FILE SIZE

React Component

Maximum

300 lines

Service

Maximum

400 lines

Repository

Maximum

300 lines

If larger,

split into multiple files.

---

# FUNCTIONS

Maximum

50 lines

Single Responsibility Principle

No deeply nested logic

Return early

Avoid duplicate code

---

# COMMENTS

Comment

Why

not

What

Avoid unnecessary comments.

Document public APIs.

---

# ERROR HANDLING

Never swallow exceptions.

Use global error handlers.

Return meaningful error messages.

Log unexpected errors.

---

# LOGGING

Log

Authentication

Authorization

Uploads

AI Requests

Database Errors

Notifications

Never log

Passwords

OTP

Secrets

Tokens

---

# API STANDARDS

REST

JSON

Versioned

Input Validation

Output Validation

Pagination

Filtering

Rate Limiting

Request IDs

---

# DATABASE

UUID Primary Keys

Soft Deletes

Foreign Keys

Indexes

Transactions

No duplicate data

---

# AI

Never call providers directly.

Always use

AI Router

Always include

Farm Memory

Always validate responses.

---

# TESTING

Every feature requires

Unit Tests

Integration Tests

API Tests

Edge Case Tests

Accessibility Tests (frontend)

---

# SECURITY

HTTPS

Firebase JWT

RBAC

Input Validation

Environment Variables

Secrets Manager

Parameterized Queries

---

# GIT

Branch Names

feature/

bugfix/

hotfix/

release/

Commit Messages

feat:

fix:

docs:

refactor:

test:

chore:

Example

feat: add crop growth timeline

---

# CODE REVIEW CHECKLIST

✓ Builds successfully

✓ Tests pass

✓ No duplicate code

✓ Proper typing

✓ Error handling

✓ Accessibility

✓ Documentation updated

✓ Security reviewed

✓ Performance considered

---

# PERFORMANCE

Use caching.

Use pagination.

Avoid unnecessary renders.

Memoize expensive operations.

Compress images.

Lazy load screens.

---

# ACCESSIBILITY

Minimum touch target

48dp

Dynamic fonts

Screen reader labels

High contrast

Voice support

Tamil-first text

---

# DOCUMENTATION

Every public function

Description

Parameters

Returns

Exceptions

Every module

README

Architecture notes

Usage examples

---

# DEPENDENCIES

Do not add new libraries without justification.

Prefer stable, well-maintained packages.

Keep dependencies updated.

---

# DEFINITION OF DONE

A task is complete only when:

✓ Feature works

✓ Tests pass

✓ Documentation updated

✓ Error handling complete

✓ Loading state added

✓ Empty state added

✓ Offline handling considered

✓ Accessibility checked

✓ Performance acceptable

✓ Security reviewed

✓ Code reviewed