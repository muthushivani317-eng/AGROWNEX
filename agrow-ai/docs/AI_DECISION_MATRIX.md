# 🤖 AGROWAI AI DECISION MATRIX

Version: Foundation Release (V1)

---

# PURPOSE

This document defines how AgrowAI selects AI models.

No feature should directly call ChatGPT or Gemini.

Every request must go through the AI Router.

The router decides

• Which model to use

• Which prompt to use

• Which context to send

• Which response format to return

This ensures consistency and makes adding future AI providers simple.

---

# AI ARCHITECTURE

Farmer

↓

AgrowAI App

↓

AI Router

↓

Request Analyzer

↓

Context Builder

↓

Model Selector

↓

Prompt Builder

↓

AI Provider

↓

Response Validator

↓

Farmer

---

# CURRENT AI PROVIDERS

ChatGPT

Purpose

General reasoning

Gemini

Purpose

Crop/plant identification, growth analysis and OCR — never disease diagnosis

Claude Code

Purpose

Software Development Only

Never used in production.

---

# MODEL RESPONSIBILITIES

ChatGPT

✔ Conversations

✔ Crop Guidance

✔ Fertilizer Advice

✔ Weather Explanation

✔ Market Explanation

✔ Government Scheme Explanation

✔ Crop Calendar

✔ Notifications

✔ Produce Listing Assistant

✔ AI Recommendations

Gemini

✔ Crop and Plant Identification

✔ Image Understanding

✔ OCR

✔ Crop Growth Analysis

✔ Soil Report Reading

✔ Fertilizer Label Reading

✔ Image Comparison

✔ Multi-image Analysis

---

# AI ROUTER

Every request enters here.

The router determines

Input Type

↓

Intent

↓

Context

↓

Model

↓

Prompt

↓

Response Format

---

# ROUTING TABLE

TEXT QUESTION

↓

ChatGPT

----------------------------

VOICE QUESTION

↓

Speech-to-Text

↓

ChatGPT

----------------------------

IMAGE

↓

Gemini

----------------------------

IMAGE + QUESTION

↓

Gemini

↓

ChatGPT

----------------------------

OCR

↓

Gemini

↓

ChatGPT

----------------------------

MULTIPLE IMAGES

↓

Gemini

↓

ChatGPT

----------------------------

SOIL REPORT PDF

↓

Gemini OCR

↓

ChatGPT

----------------------------

FERTILIZER LABEL

↓

Gemini OCR

↓

ChatGPT

----------------------------

WEATHER

↓

Weather API

↓

ChatGPT

----------------------------

MARKET PRICE

↓

Market API

↓

ChatGPT

----------------------------

GOVERNMENT SCHEME

↓

Verified Database

↓

ChatGPT

----------------------------

SELL MY PRODUCE

↓

ChatGPT

----------------------------

CROP GROWTH

↓

Gemini

↓

ChatGPT

----------------------------

DISEASE DETECTION

(Updated 2026-08 — see app.modules.disease.farmer_diagnosis_service module
docstring for full rationale. This replaces the original V1 rule below, which
predates the OpenAI vision integration and the discovery that most of the
locally-trained classifiers are provisional/public-dataset models not yet
validated on real farmer photos.)

General farmer release (any authenticated farmer, any crop) —
POST /disease/predict:

↓

OpenAI vision diagnosis (primary signal, always shown to the farmer)

↓

Cross-checked against a dedicated crop-specific ONNX/PyTorch classifier where
one exists (banana; chilli/redgram and paddy/cotton/groundnut as a
background cross-check signal only — those five remain
RESTRICTED_INTERNAL_TESTING_ONLY / ungated-for-general-release as a primary
answer)

↓

Response is always labeled `verification_level`: `verified_by_local_model`
(classifier independently agreed) or `ai_vision_estimate` (no classifier for
this crop, or it disagreed) — the app must never present these with equal
visual confidence, and disagreement always forces `needs_expert_review`

Controlled-tester release (internal/pilot tester, KVK reviewer roles only —
banana_v3 / restricted_crops / legacy_joint routes):

↓

Dedicated crop-specific ONNX/PyTorch classifier only

↓

Verified disease registry (accepted labels only)

Unsupported crop/class → fail closed; no generative fallback

No chemical/pesticide brand recommendations in either release path.

----------------------------

IMAGE COMPARISON

↓

Gemini

----------------------------

WEEKLY PROGRESS

↓

Gemini

↓

ChatGPT

----------------------------

AI MEMORY

↓

Database

↓

ChatGPT

---

# CONTEXT BUILDER

Every AI request automatically includes

Farmer Profile

Farm

Crop

Growth Stage

Disease History

Weather

Fertilizer History

Weekly Images

Recent Conversations

Produce Listings

Current Language

Location

The farmer should never repeat this information.

---

# PROMPT SELECTION

Disease

↓

General farmer release: OpenAI vision prompt, cross-checked against a
dedicated crop classifier where available; response always labeled
`verified_by_local_model` or `ai_vision_estimate` (see DISEASE DETECTION
above)

Controlled-tester release: dedicated crop classifier + verified registry
only (no generative prompt)

Weather

↓

Weather Prompt

Crop Growth

↓

Growth Prompt

Government Scheme

↓

Scheme Prompt

Produce

↓

Produce Prompt

General Chat

↓

Conversation Prompt

---

# RESPONSE VALIDATOR

Every AI response is checked before sending.

Verify

No fabricated weather

No fabricated market prices

No fabricated schemes

No unsupported medical claims

No dangerous chemical recommendations

No unsupported yield guarantees

---

# RESPONSE FORMAT

Summary

↓

Explanation

↓

Recommendation

↓

Precautions

↓

Next Step

Maximum

200 words

---

# AI MEMORY PRIORITY

Before every AI request

Load

Profile

↓

Farm

↓

Crop

↓

Weather

↓

Disease History

↓

Growth

↓

Previous Advice

↓

Current Question

Only then call the AI.

---

# FAILOVER STRATEGY

If Gemini fails

↓

Retry

↓

If still fails

↓

Return friendly error

↓

Allow re-upload

--------------------------------

If ChatGPT fails

↓

Retry

↓

Cached Response

↓

Friendly Error

---

# LOGGING

Log

Provider

Model

Prompt Version

Latency

Tokens

Errors

Response Time

Cost

Do not log personal conversations unnecessarily.

---

# COST OPTIMIZATION

Use ChatGPT only when reasoning is needed.

Use Gemini only for image understanding.

Do not call multiple models unless required.

Cache repeated responses where safe.

---

# FUTURE AI PROVIDERS

Architecture must allow adding

OpenAI GPT

Gemini

Anthropic

Local LLM

Agriculture Models

Satellite AI

Voice AI

Without changing application logic.

---

# SAFETY RULES

Always state uncertainty.

Never fabricate.

Never hide uncertainty.

Never invent prices.

Never invent weather.

Never invent schemes.

Never recommend unsafe pesticide usage.

Never recommend commercial brands by default.

Always encourage farmers to consult local agriculture experts when confidence is low.

---

# FARM MEMORY FLOW

Farmer

↓

Farm

↓

Crop Session

↓

Disease

↓

Growth

↓

Weather

↓

Fertilizer

↓

AI Conversation

↓

AI Memory

↓

Context Builder

↓

Prompt Builder

↓

AI

↓

Personalized Recommendation

---

# DECISION MATRIX

| Request | Primary Model | Secondary Model |
|----------|---------------|-----------------|
| General Question | ChatGPT | — |
| Disease Detection (general farmer release) | OpenAI vision | Crop-specific ONNX/PyTorch classifier where available (cross-check only; labeled verified_by_local_model / ai_vision_estimate) |
| Disease Detection (controlled-tester release) | Crop-specific ONNX/PyTorch classifier | Verified registry; otherwise fail closed |
| Crop Growth Monitor | Gemini | ChatGPT |
| Weekly Image Comparison | Gemini | ChatGPT |
| Soil Report PDF | Gemini | ChatGPT |
| Fertilizer Label OCR | Gemini | ChatGPT |
| Weather Advice | ChatGPT | Weather API |
| Market Price Explanation | ChatGPT | Market API |
| Government Scheme | ChatGPT | Verified Database |
| Produce Listing | ChatGPT | — |
| AI Memory Search | Database | ChatGPT |
| Voice Question | Whisper → ChatGPT | — |
| Image + Voice | Gemini → ChatGPT | — |
| Multi-image Analysis | Gemini | ChatGPT |

---

# SUCCESS CRITERIA

Every AI response should be

✔ Accurate

✔ Personalized

✔ Simple

✔ Actionable

✔ Tamil First

✔ Safe

✔ Context Aware

✔ Fast

Target Response Time

Text

< 3 seconds

Image

< 8 seconds

OCR

< 10 seconds

Voice

< 5 seconds
