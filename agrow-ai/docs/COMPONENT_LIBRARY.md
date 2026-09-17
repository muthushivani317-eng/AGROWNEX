# 🧩 AGROWAI COMPONENT LIBRARY

Version: Foundation Release (V1)

---

# PURPOSE

This document defines every reusable UI component used across AgrowAI.

Goals

• Consistency

• Reusability

• Accessibility

• Performance

• Tamil-first UX

No screen should create custom UI if a reusable component already exists.

---

# COMPONENT NAMING

All reusable components must start with

Ag

Examples

AgButton

AgCard

AgInput

AgBottomSheet

AgWeatherCard

AgDiseaseCard

AgGrowthCard

---

# COMPONENT CATEGORIES

Foundation

Forms

Cards

Navigation

AI

Media

Feedback

Charts

Timeline

Dialogs

Maps

Voice

Notifications

---

# FOUNDATION COMPONENTS

## AgButton

Purpose

Primary action button.

Variants

Primary

Secondary

Outline

Ghost

Danger

Success

Loading

Disabled

Props

title

icon

loading

disabled

onPress

fullWidth

size

Accessibility

Minimum height 56dp

Supports Tamil text

Loading animation

---

## AgIconButton

Purpose

Icon only button.

Sizes

Small

Medium

Large

Supports

Ripple

Tooltip

Accessibility labels

---

## AgText

Purpose

Typography wrapper.

Variants

HeadingXL

HeadingL

HeadingM

HeadingS

Body

Caption

Label

Support

Tamil

English

Dynamic font scaling

---

## AgCard

Purpose

Reusable container.

Props

title

subtitle

icon

actions

children

Variants

Default

Elevated

Outlined

Compact

---

# FORM COMPONENTS

## AgInput

Supports

Text

Number

Phone

Email

Password

Tamil typing

Validation

Character counter

Error state

Helper text

---

## AgSearchBar

Supports

Voice search

Search history

Suggestions

Clear button

---

## AgDropdown

Supports

Single select

Multi select

Search

Lazy loading

---

## AgDatePicker

Used for

Sowing Date

Harvest Date

Calendar

Reminders

---

## AgLocationPicker

Supports

GPS

Manual selection

Map selection

Village lookup

---

# FARM COMPONENTS

## AgFarmCard

Displays

Farm name

Crop

Area

Status

Health score

Weather

Quick actions

---

## AgCropCard

Displays

Crop

Variety

Growth stage

Days since sowing

---

## AgFarmBoundaryView

Displays

Farm polygon

Area

GPS

Satellite layer (future)

---

# AI COMPONENTS

## AgChatBubble

Supports

Markdown

Images

Voice

Streaming

Quick replies

Timestamp

---

## AgTypingIndicator

Animated

Three dots

---

## AgSuggestionChip

Quick AI prompts.

Example

"Why are my leaves yellow?"

---

## AgVoiceRecorder

Record

Pause

Cancel

Playback

Waveform

---

# WEATHER COMPONENTS

## AgWeatherCard

Displays

Temperature

Humidity

Rain

Wind

UV

Alert

---

## AgWeatherForecast

7-day forecast

Horizontal scroll

---

# DISEASE COMPONENTS

## AgDiseaseCard

Displays

Disease

Confidence

Symptoms

Severity

Recommendation

---

## AgDiseaseTimeline

Displays

All previous detections.

---

# GROWTH COMPONENTS

## AgGrowthCard

Displays

Health Score

Growth Stage

Trend

Recommendation

---

## AgGrowthTimeline

Weekly photos

Health trend

AI comments

---

## AgImageComparison

Before

After

Slider

---

# MARKET COMPONENTS

## AgMarketPriceCard

Displays

Crop

Today's price

Trend

Last update

Source

---

## AgTrendChart

Price history

Weekly

Monthly

Yearly

---

# GOVERNMENT COMPONENTS

## AgSchemeCard

Displays

Scheme

Benefits

Eligibility

Deadline

Official source

---

# PRODUCE COMPONENTS

## AgProduceCard

Displays

Crop

Quantity

Harvest Date

Status

Expected Price

---

## AgProduceGallery

Multiple images

Zoom

Delete

Add

---

# NOTIFICATION COMPONENTS

## AgNotificationCard

Displays

Icon

Title

Message

Priority

Time

Read status

---

# MEDIA COMPONENTS

## AgCameraView

Take photo

Flash

Zoom

Crop overlay

---

## AgImageViewer

Zoom

Rotate

Download

Share

---

# MAP COMPONENTS

## AgMapView

Farm

GPS

Markers

Boundaries

---

# FEEDBACK COMPONENTS

AgSnackbar

AgToast

AgLoading

AgSkeleton

AgEmptyState

AgErrorState

AgOfflineBanner

---

# DIALOGS

AgConfirmationDialog

AgSuccessDialog

AgErrorDialog

AgPermissionDialog

---

# ACCESSIBILITY

Every component

Screen reader

Tamil labels

48dp touch target

High contrast

Dynamic font size

Keyboard navigation where applicable

---

# PERFORMANCE

Memoized

Lazy loaded

Optimized rendering

Image caching

Minimal re-renders

---

# QUALITY CHECKLIST

Every component must have

Documentation

Props

Variants

Loading state

Error state

Accessibility support

Dark mode

Unit tests

Storybook example (future)

---

# FUTURE COMPONENTS

AgSatelliteView

AgDroneViewer

AgYieldChart

AgIoTDashboard

AgExpertConnectCard

AgCarbonCreditCard

AgWarehouseCard

AgBuyerCard
