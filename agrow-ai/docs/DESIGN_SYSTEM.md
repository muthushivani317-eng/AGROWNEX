    # 🌾 AGROWAI DESIGN SYSTEM

Version: Foundation Release (V1)

---

# PURPOSE

This document defines the complete visual language and design system for AgrowAI.

Every screen, component, animation and interaction must follow this specification.

The goal is to create a modern, premium, accessible and farmer-friendly application.

---

# DESIGN PHILOSOPHY

AgrowAI should feel

• Premium

• Trustworthy

• Simple

• Calm

• Fast

• Modern

The UI should never feel crowded.

Farmers should immediately understand what to do.

Technology should stay in the background.

The farming experience should remain the focus.

---

# DESIGN PRINCIPLES

1.

Farmer First

Design for people with low digital literacy.

2.

Tamil First

Tamil is the primary language.

3.

Camera First

Encourage taking photos instead of typing.

4.

Voice First

Allow speaking instead of typing whenever possible.

5.

Minimal Typing

Reduce keyboard usage.

6.

Offline Friendly

Gracefully handle poor internet.

7.

One-Hand Friendly

Every important action should be reachable with one hand.

---

# BRAND

Product

AgrowAI

Tagline

Your AI Farming Partner

Brand Personality

Helpful

Friendly

Reliable

Intelligent

Simple

Professional

---

# COLOR PALETTE

Primary Green

#2E7D32

Light Green

#4CAF50

Dark Green

#1B5E20

Success

#43A047

Warning

#F9A825

Danger

#E53935

Info

#1E88E5

Background

#F7F9F4

Surface

#FFFFFF

Border

#E5E7EB

Primary Text

#111827

Secondary Text

#6B7280

Disabled

#9CA3AF

---

# DARK MODE

Background

#121212

Surface

#1E1E1E

Card

#252525

Primary Text

#FFFFFF

Secondary Text

#BDBDBD

Border

#333333

---

# TYPOGRAPHY

English Font

Inter

Tamil Font

Noto Sans Tamil

Heading XL

32

Heading L

28

Heading M

24

Heading S

20

Body Large

18

Body

16

Body Small

14

Caption

12

Button

16

Line Height

1.5

---

# SPACING

4

8

12

16

20

24

32

40

48

64

Use 8-point grid.

---

# BORDER RADIUS

Small

8

Medium

12

Large

20

Cards

24

Floating Button

999

---

# ELEVATION

Low

2dp

Medium

6dp

High

12dp

Dialogs

24dp

---

# ICONS

Library

Lucide

Size

20

24

32

40

48

Icons

Home

Farm

Disease

AI

Market

Profile

Camera

Weather

Water

Government

Growth

Notification

GPS

Voice

Calendar

---

# BUTTONS

Primary

Filled Green

Secondary

Outlined

Danger

Red

Ghost

Transparent

Icon

Circular

FAB

Floating Green

Loading

Animated

Disabled

Grey

Minimum Height

56dp

---

# INPUTS

Text Field

Dropdown

Search

OTP

Date Picker

Time Picker

GPS Picker

Voice Input

Camera Input

Image Picker

---

# CARDS

Farm Card

Weather Card

Disease Card

Growth Card

Produce Card

Government Scheme Card

Market Card

Notification Card

AI Suggestion Card

Every card should have

Rounded corners

Light shadow

Large spacing

Simple hierarchy

---

# NAVIGATION

Bottom Navigation

Home

AI

Farm

Market

Profile

Maximum

5 tabs

---

# HOME SCREEN

Greeting

Current Weather

Farm Health

Today's Tasks

Crop Growth

AI Recommendations

Disease Detection

Market Prices

Notifications

Sell Produce

---

# COMPONENTS

App Bar

Bottom Navigation

Bottom Sheet

Modal

Dialog

Search Bar

Segmented Control

Chip

Avatar

Badge

Progress Bar

Timeline

Accordion

Carousel

Tooltip

Snackbar

Toast

Loading Spinner

Skeleton Loader

Empty State

Error State

Offline Banner

---

# IMAGE COMPONENTS

Camera Preview

Image Viewer

Before / After Comparison

Crop Timeline

Disease Result

Gallery

Zoom

---

# LISTS

Simple List

Grouped List

Timeline List

Grid

Card List

Section List

---

# ANIMATIONS

Splash

Fade

Slide

Scale

Card Hover

Bottom Sheet

Loading

Skeleton

Success

Error

Use subtle animations.

Avoid distracting effects.

---

# ACCESSIBILITY

Minimum Touch Target

48dp

Large Text Support

Yes

Screen Reader

Yes

Voice Navigation

Yes

High Contrast

Yes

Color Blind Friendly

Yes

---

# RESPONSIVE DESIGN

Phones

Small Phones

Large Phones

Tablets

Foldables

Landscape

---

# FARMER UX RULES

Maximum taps

5

Never show more than

3 primary actions

Avoid long forms.

Use

Camera

Voice

GPS

instead of typing.

Remember previous selections.

Auto-fill data.

---

# OFFLINE UX

Store

Farm Data

Profile

AI History

Growth Images

Queue uploads.

Sync automatically.

Show sync status.

---

# LOADING STATES

Every screen must include

Skeleton

Progress

Retry

Offline

Timeout

---

# ERROR STATES

Friendly messages

Retry button

Help button

Contact Support

---

# AI DESIGN

Chat should look natural.

Streaming response.

Typing indicator.

Voice playback.

Image preview.

Quick suggestions.

Conversation history.

---

# NOTIFICATIONS

Priority

Critical

High

Medium

Low

Grouped by category.

Allow swipe actions.

---

# PERFORMANCE

Launch under 2 seconds.

60 FPS animations.

Lazy loading.

Image caching.

Offline cache.

---

# SECURITY UX

Biometric support.

Session timeout.

Secure logout.

Confirmation dialogs.

---

# QUALITY RULES

Every screen must include

Loading

Error

Empty

Offline

Accessibility

Dark Mode

Responsive Layout

Animation

No exceptions.

---

# FUTURE SUPPORT

Admin Dashboard

FPO Dashboard

Buyer Dashboard

Tablet Layout

Desktop Layout

Smart Watch Notifications

Wearables

AI Glasses

Voice Assistant

IoT Dashboard

Satellite Dashboard

Drone Dashboard

# 🌾 AGROWAI USER FLOWS

Version: Foundation Release (V1)

---

# PURPOSE

This document defines every end-to-end journey inside AgrowAI.

Every feature must follow these flows.

The objective is to minimize user effort while maximizing value.

---

# PRIMARY USER TYPES

• Farmer

• FPO

• Agriculture Officer

• Admin

Future

• Buyer

• Warehouse

• Insurance

---

# FARMER JOURNEY

New Farmer

↓

Install App

↓

Language Selection

↓

Phone Login

↓

OTP Verification

↓

Create Profile

↓

Register Farm

↓

Home Dashboard

↓

Use AI Features

↓

Receive Notifications

↓

Monitor Crop

↓

Sell Produce

---

# FIRST TIME USER FLOW

Launch App

↓

Splash Screen

↓

Choose Language

↓

Tamil

↓

Phone Number

↓

OTP Verification

↓

Permissions

Location

Camera

Notification

Microphone

↓

Create Farmer Profile

↓

Register First Farm

↓

Welcome Dashboard

Estimated Time

Less than 3 minutes

---

# LOGIN FLOW

Open App

↓

Auto Login?

↓

YES

↓

Home

NO

↓

Phone Login

↓

OTP

↓

Authenticated

↓

Dashboard

---

# FARM REGISTRATION FLOW

Home

↓

Add Farm

↓

Farm Name

↓

GPS Detection

↓

Draw Farm Boundary

↓

Crop

↓

Variety

↓

Area

↓

Soil Type

↓

Irrigation

↓

Save Farm

↓

Dashboard

---

# AI CHAT FLOW

Home

↓

AI Assistant

↓

Choose Input

Text

Voice

Camera

Gallery

↓

AI Router

↓

ChatGPT / Gemini

↓

Response

↓

Save Conversation

↓

AI Memory Updated

---

# DISEASE DETECTION FLOW

Home

↓

Disease Detection

↓

Take Photo

↓

AI Analysis

↓

Disease Result

↓

Recommendation

↓

Save Detection

↓

Update Crop History

↓

Notify Farmer

---

# CROP GROWTH MONITOR FLOW

Dashboard

↓

Crop Growth

↓

Weekly Upload

↓

AI Analysis

↓

Health Score

↓

Timeline Update

↓

Weekly Comparison

↓

Recommendation

↓

AI Memory Updated

---

# FERTILIZER FLOW

Home

↓

Fertilizer Advisor

↓

Crop

↓

Growth Stage

↓

Area

↓

Soil

↓

AI Recommendation

↓

Save Recommendation

↓

Reminder Created

---

# WEATHER FLOW

Dashboard

↓

Weather

↓

GPS

↓

Open-Meteo

↓

Forecast

↓

Spraying Advice

↓

Irrigation Advice

↓

Weather Alerts

---

# MARKET PRICE FLOW

Dashboard

↓

Market

↓

Crop

↓

Nearby Market

↓

Today's Price

↓

Price Trend

↓

AI Summary

---

# GOVERNMENT SCHEME FLOW

Dashboard

↓

Government Schemes

↓

Farmer Profile

↓

Eligibility

↓

Verified Schemes

↓

Details

↓

Official Link

---

# SELL MY PRODUCE FLOW

Dashboard

↓

Sell My Produce

↓

Select Farm

↓

Crop

↓

Quantity

↓

Harvest Date

↓

Expected Price

↓

Photos

↓

Publish

↓

Available for Procurement

---

# NOTIFICATION FLOW

Weather Alert

↓

AI Recommendation

↓

Notification Created

↓

Push Notification

↓

Notification Center

↓

Farmer Opens

↓

Action Screen

---

# PROFILE FLOW

Profile

↓

Edit

↓

Update

↓

Save

↓

Database Updated

↓

AI Memory Updated

---

# OFFLINE FLOW

No Internet

↓

Offline Banner

↓

Save Locally

↓

Queue Request

↓

Internet Available

↓

Auto Sync

↓

Success

---

# AI MEMORY FLOW

Farmer

↓

Farm

↓

Crop Session

↓

Weekly Photos

↓

Disease History

↓

Weather History

↓

Fertilizer

↓

Produce Listings

↓

AI Conversation

↓

Memory Engine

↓

Personalized Response

---

# ADMIN FLOW

Admin Login

↓

Dashboard

↓

Users

↓

Farmers

↓

Farms

↓

Disease Reports

↓

Market Prices

↓

Government Schemes

↓

Notifications

↓

Analytics

---

# FPO FLOW

Login

↓

Member Farmers

↓

Crop Summary

↓

Disease Trends

↓

Produce Availability

↓

Upcoming Harvest

↓

Reports

---

# FUTURE BUYER FLOW

Buyer Login

↓

Search Crop

↓

District

↓

Village

↓

Quantity

↓

Contact Procurement Team

---

# EDGE CASES

Invalid OTP

↓

Retry

No Internet

↓

Offline Mode

AI Failure

↓

Fallback Response

Camera Permission Denied

↓

Permission Screen

GPS Disabled

↓

Manual Selection

Image Upload Failed

↓

Retry

Server Down

↓

Maintenance Screen

---

# UX RULES

Maximum taps

5

Maximum onboarding

3 minutes

Maximum loading

2 seconds

Always provide

Loading

Empty

Error

Offline

Retry

States

---

# SUCCESS METRICS

Farmer onboarding completion

Average AI response time

Disease detection usage

Weekly growth uploads

Produce listings

Notification engagement

Weekly active farmers

Farmer retention