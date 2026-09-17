# 🌾 AGROWAI DATABASE SCHEMA

Version: Foundation Release (V1)

---

# PURPOSE

This document defines the complete database architecture for AgrowAI.

It serves as the single source of truth for every database table, relationship, constraint, index, and future migration.

Every backend service must follow this specification.

---

# DATABASE OVERVIEW

Database

PostgreSQL 16+

Extensions

• PostGIS
• UUID Extension
• pg_trgm
• pgcrypto

Cache

Redis

Object Storage

AWS S3

ORM

SQLAlchemy

Migration Tool

Alembic

---

# DATABASE DESIGN PRINCIPLES

The database must be

• Scalable

• Secure

• Highly normalized

• Optimized for large datasets

• Optimized for millions of farmers

• Easy to extend

• AI Ready

• Analytics Ready

• Audit Ready

• Offline Sync Ready

---

# PRIMARY KEYS

Every table must use

UUID

Never use auto increment integers.

Example

farmer_id

UUID

farm_id

UUID

crop_id

UUID

---

# TIMESTAMPS

Every table must include

created_at

updated_at

deleted_at

created_by

updated_by

Soft delete should be used wherever practical.

Never permanently delete production records unless explicitly required.

---

# AUDITABILITY

Every important action must be traceable.

Examples

Farmer Registered

Farm Updated

Disease Detection

Produce Listed

Notification Sent

AI Recommendation Generated

Every change should be recoverable.

---

# SOFT DELETE POLICY

Records should not be permanently removed.

Instead

deleted_at

is set.

Benefits

• Recovery

• Analytics

• Compliance

• History

---

# NAMING CONVENTIONS

Tables

snake_case

Examples

farmer_profiles

farm_locations

crop_sessions

produce_listings

Columns

snake_case

Examples

farmer_id

crop_name

created_at

Indexes

idx_

Foreign Keys

fk_

Unique Constraints

uq_

Check Constraints

chk_

---

# RELATIONSHIP RULES

One Farmer

↓

Many Farms

One Farm

↓

Many Crop Sessions

One Crop Session

↓

Many Disease Detections

One Crop Session

↓

Many Weekly Growth Records

One Crop Session

↓

Many AI Conversations

One Farmer

↓

Many Produce Listings

One Farmer

↓

Many Notifications

---

# DATABASE MODULES

The database is divided into modules.

Module 1

Authentication

Module 2

Farmer Profile

Module 3

Farm Registration

Module 4

Crop Management

Module 5

Disease Detection

Module 6

Weather

Module 7

Fertilizer Advisor

Module 8

Crop Growth Monitor

Module 9

Crop Calendar

Module 10

Market Prices

Module 11

Government Schemes

Module 12

Sell My Produce

Module 13

Notifications

Module 14

AI Memory

Module 15

Administration

Module 16

Audit Logs

Module 17

Analytics

---

# DATABASE STANDARDS

Never duplicate information.

Instead

Reference using foreign keys.

Example

Wrong

Store farmer name in every table.

Correct

Store farmer_id.

---

# FILE STORAGE

Large files should never be stored inside PostgreSQL.

Images

↓

AWS S3

Videos

↓

AWS S3

Documents

↓

AWS S3

Database stores only

file_url

file_type

file_size

mime_type

uploaded_at

---

# GPS STORAGE

Use PostGIS.

Store

Latitude

Longitude

Farm Boundary Polygon

Area

Spatial Index

This enables

Nearby services

Weather

Satellite monitoring

Future drone support

---

# AI MEMORY DESIGN

AI should never rely only on the latest message.

Store

Farmer Profile

Farm Details

Crop History

Disease History

Weather History

Weekly Images

Fertilizer History

Produce Listings

AI Conversations

Recommendations

This allows personalized AI responses.

---

# NOTIFICATION SYSTEM

Notifications are stored permanently.

Every notification contains

Title

Message

Category

Priority

Read Status

Created Time

Delivery Status

Notification Types

Weather

Disease

Government Scheme

Market Price

Reminder

AI Recommendation

General

---

# AUDIT LOGGING

Every critical action must generate an audit log.

Examples

Login

Logout

Profile Update

Farm Registration

Disease Detection

Produce Listing

Notification Sent

Admin Update

AI Recommendation

Audit logs should never be deleted.

---

# SECURITY

Passwords

Never stored.

Authentication

Firebase Authentication.

Sensitive Data

Encrypted.

API Keys

Never stored inside database.

Use environment variables.

---

# PERFORMANCE

Every foreign key must be indexed.

Every frequently searched column must be indexed.

Pagination required.

No SELECT * queries.

Use connection pooling.

Optimize joins.

Avoid unnecessary JSON fields.

---

# SCALABILITY

The database should support

10 Million Farmers

100 Million AI Conversations

500 Million Images

1 Billion Notifications

Future expansion should require minimal schema changes.

---

# BACKUP STRATEGY

Daily Backup

Incremental Backup

Point-in-Time Recovery

Disaster Recovery Plan

Database replication should be supported.

---

# VERSIONING

All schema changes must be handled through Alembic migrations.

Never manually edit production tables.

Every migration must be reversible.

---

# FUTURE MODULES

Reserved tables for

IoT Devices

Satellite Monitoring

Drone Flights

Yield Prediction

Insurance

Credit

Warehouse

Cold Storage

Buyer Network

Machine Rental

Carbon Credits

Future AI Models

These modules should integrate without breaking existing relationships.
# PART 2 - USER DOMAIN

This section defines all tables related to authentication, user management, farmer profiles and farms.

---

# MODULE OVERVIEW

```
Authentication
      │
      ▼
Users
      │
      ▼
Farmer Profile
      │
      ▼
Farms
      │
      ▼
Farm Members
      │
      ▼
Farm Media
```

---

# TABLE LIST

Authentication

- users
- user_sessions
- refresh_tokens
- otp_requests
- login_history

Authorization

- roles
- permissions
- role_permissions
- user_roles

Farmer

- farmer_profiles
- farmer_languages
- farmer_preferences
- emergency_contacts

Farm

- farms
- farm_boundaries
- farm_locations
- farm_members
- farm_media

Total Tables

18

---

# TABLE : users

Purpose

Stores every authenticated user.

Primary Key

user_id UUID

Columns

user_id UUID PRIMARY KEY

firebase_uid VARCHAR(255) UNIQUE NOT NULL

phone_number VARCHAR(20)

email VARCHAR(255)

is_phone_verified BOOLEAN

is_email_verified BOOLEAN

status VARCHAR(30)

last_login TIMESTAMP

created_at TIMESTAMP

updated_at TIMESTAMP

deleted_at TIMESTAMP

Indexes

firebase_uid

phone_number

email

Relationships

One User

↓

One Farmer Profile

One User

↓

Many Sessions

One User

↓

Many Farms

---

# TABLE : otp_requests

Purpose

Track OTP verification.

Columns

otp_id UUID

user_id UUID

phone_number

otp_hash

expires_at

attempt_count

verified

created_at

Indexes

phone_number

user_id

expires_at

---

# TABLE : refresh_tokens

Purpose

Store refresh tokens.

Columns

token_id UUID

user_id UUID

device_id

token_hash

expires_at

revoked

created_at

---

# TABLE : user_sessions

Purpose

Track logged-in devices.

Columns

session_id UUID

user_id UUID

device_name

device_type

ip_address

location

last_active

created_at

---

# TABLE : login_history

Purpose

Audit login activity.

Columns

history_id UUID

user_id UUID

login_method

device

platform

ip

success

created_at

---

# TABLE : roles

Purpose

Role master.

Default Roles

Farmer

FPO

Agriculture Officer

Buyer

Admin

Super Admin

Columns

role_id UUID

role_name

description

created_at

---

# TABLE : permissions

Purpose

Permission master.

Examples

farm.create

farm.update

farm.delete

market.publish

admin.manage

Columns

permission_id UUID

permission_name

description

---

# TABLE : role_permissions

Purpose

Assign permissions.

Columns

id UUID

role_id

permission_id

---

# TABLE : user_roles

Purpose

Assign users to roles.

Columns

id UUID

user_id

role_id

---

# TABLE : farmer_profiles

Purpose

Main farmer profile.

Columns

farmer_id UUID

user_id UUID

full_name

gender

date_of_birth

language

district

block

village

profile_photo

experience_years

education

primary_crop

secondary_crop

created_at

updated_at

Indexes

district

block

village

primary_crop

Relationships

One Farmer

↓

Many Farms

One Farmer

↓

Many Produce Listings

One Farmer

↓

Many AI Chats

---

# TABLE : farmer_languages

Purpose

Store supported languages.

Columns

id UUID

farmer_id

language_code

is_default

---

# TABLE : farmer_preferences

Purpose

User settings.

Columns

id UUID

farmer_id

theme

notifications_enabled

voice_enabled

preferred_units

default_crop

---

# TABLE : emergency_contacts

Purpose

Emergency family contacts.

Columns

id UUID

farmer_id

name

phone

relationship

---

# TABLE : farms

Purpose

Store registered farms.

Columns

farm_id UUID

farmer_id UUID

farm_name

crop

crop_variety

soil_type

irrigation_type

area

unit

planting_date

status

created_at

updated_at

Indexes

farmer_id

crop

status

---

# TABLE : farm_locations

Purpose

GPS location.

Columns

location_id UUID

farm_id UUID

latitude

longitude

elevation

address

district

block

village

PostGIS Point

---

# TABLE : farm_boundaries

Purpose

Polygon boundary.

Columns

boundary_id UUID

farm_id UUID

polygon_geometry

area

perimeter

created_at

Spatial Index

GiST

---

# TABLE : farm_members

Purpose

Multiple users can manage one farm.

Columns

id UUID

farm_id

user_id

role

joined_at

---

# TABLE : farm_media

Purpose

Store farm photos.

Actual images remain in AWS S3.

Columns

media_id UUID

farm_id UUID

file_url

file_name

mime_type

file_size

uploaded_by

created_at

---

# RELATIONSHIP SUMMARY

User

↓

Farmer Profile

↓

Farm

↓

Farm Location

↓

Farm Boundary

↓

Farm Media

↓

Future Modules

Disease Detection

Crop Growth

Weather

AI Memory

Produce Listing

# PART 3 – FARM INTELLIGENCE DOMAIN

This module stores all agricultural data used by AgrowAI AI services.

Every agricultural record belongs to a Crop Session.

Relationship

Farmer
    ↓
Farm
    ↓
Crop Session
    ├── Disease Detection
    ├── Weekly Growth
    ├── Fertilizer Applications
    ├── Weather History
    ├── Irrigation
    ├── AI Conversations
    ├── AI Recommendations
    ├── Crop Calendar
    └── Harvest

---

TABLE LIST

Master Data

• crops
• crop_varieties
• growth_stages
• soil_types
• irrigation_types

Crop Management

• crop_sessions
• crop_calendar_events

Disease

• disease_detections
• disease_images
• disease_recommendations

Weather

• weather_history
• weather_alerts

Fertilizer

• fertilizer_recommendations
• fertilizer_applications

Growth

• weekly_growth
• growth_images
• growth_reports

AI Memory

• ai_conversations
• ai_messages
• ai_recommendations
• ai_memory

Total Tables

18

==================================================

TABLE : crops

Purpose

Master list of supported crops.

Columns

crop_id UUID

crop_name

scientific_name

category

image_url

status

created_at

Indexes

crop_name

==================================================

TABLE : crop_varieties

Purpose

Store crop varieties.

Columns

variety_id UUID

crop_id

variety_name

description

created_at

Relationship

One Crop

↓

Many Varieties

==================================================

TABLE : growth_stages

Purpose

Master growth stages.

Examples

Seed

Germination

Vegetative

Flowering

Fruiting

Harvest

Columns

stage_id UUID

crop_id

stage_name

display_order

==================================================

TABLE : crop_sessions

Purpose

Most important table.

One record represents one crop grown on one farm during one season.

Everything connects here.

Columns

crop_session_id UUID

farm_id UUID

crop_id UUID

variety_id UUID

season_year

planting_date

expected_harvest_date

actual_harvest_date

current_growth_stage

status

created_at

updated_at

Indexes

farm_id

crop_id

status

Relationship

One Crop Session

↓

Many Disease Records

↓

Many Weekly Images

↓

Many AI Chats

↓

Many Fertilizer Records

↓

Many Weather Records

==================================================

TABLE : disease_detections

Purpose

Store every disease analysis.

Columns

detection_id UUID

crop_session_id

image_id

detected_disease

confidence_score

severity

symptoms

recommendation

model_name

created_at

Indexes

crop_session_id

detected_disease

created_at

==================================================

TABLE : disease_images

Purpose

Original uploaded images.

Image stored in AWS S3.

Columns

image_id UUID

crop_session_id

file_url

thumbnail_url

capture_method

camera_metadata

uploaded_at

==================================================

TABLE : disease_recommendations

Purpose

Recommendations linked to detections.

Columns

recommendation_id UUID

detection_id

recommendation_type

recommendation_text

priority

is_completed

created_at

==================================================

TABLE : fertilizer_recommendations

Purpose

AI-generated fertilizer advice.

Columns

recommendation_id UUID

crop_session_id

growth_stage

soil_type

recommended_n

recommended_p

recommended_k

micronutrients

application_method

recommended_date

ai_provider

created_at

==================================================

TABLE : fertilizer_applications

Purpose

Record actual fertilizer usage.

Columns

application_id UUID

crop_session_id

fertilizer_name

quantity

unit

application_date

notes

created_at

==================================================

TABLE : weather_history

Purpose

Store weather snapshots used by AI.

Columns

weather_id UUID

crop_session_id

observation_date

temperature

humidity

rainfall

wind_speed

uv_index

weather_condition

created_at

Indexes

crop_session_id

observation_date

==================================================

TABLE : weather_alerts

Purpose

Weather notifications.

Columns

alert_id UUID

crop_session_id

alert_type

severity

message

valid_from

valid_to

is_read

created_at

==================================================

TABLE : weekly_growth

Purpose

Crop Growth Monitor.

Columns

growth_id UUID

crop_session_id

week_number

health_score

growth_stage

leaf_colour

disease_status

growth_status

notes

created_at

==================================================

TABLE : growth_images

Purpose

Weekly uploaded images.

Columns

image_id UUID

growth_id

file_url

thumbnail_url

captured_at

==================================================

TABLE : growth_reports

Purpose

AI weekly reports.

Columns

report_id UUID

growth_id

summary

recommendations

comparison_previous_week

health_delta

risk_level

created_at

==================================================

TABLE : crop_calendar_events

Purpose

Automatic farming schedule.

Columns

event_id UUID

crop_session_id

event_type

title

description

scheduled_date

completed

created_at

==================================================

TABLE : ai_conversations

Purpose

Conversation sessions.

Columns

conversation_id UUID

farmer_id

crop_session_id

title

started_at

ended_at

==================================================

TABLE : ai_messages

Purpose

Store every message.

Columns

message_id UUID

conversation_id

sender

message

language

model_used

token_count

created_at

==================================================

TABLE : ai_recommendations

Purpose

Every recommendation produced by AI.

Columns

recommendation_id UUID

crop_session_id

category

recommendation

confidence

status

created_at

==================================================

TABLE : ai_memory

Purpose

Long-term memory used by AgrowAI.

Columns

memory_id UUID

farmer_id

crop_session_id

memory_type

summary

embedding_reference

importance_score

last_used

created_at

Memory Types

Crop

Disease

Weather

Fertilizer

Growth

Market

Conversation

Government Scheme

Produce Listing

==================================================

AI MEMORY FLOW

Farmer

↓

Farm

↓

Crop Session

↓

Disease Detection

↓

Weather

↓

Growth Photos

↓

Fertilizer

↓

AI Conversation

↓

AI Memory

↓

Personalized Recommendations

==================================================

FUTURE EXTENSIONS

This schema supports future additions without redesign:

• Satellite monitoring
• Drone imagery
• IoT sensors
• Yield prediction
• Fruit counting
• Leaf counting
• Canopy estimation
• Pest outbreak prediction
• Quality grading
• Carbon credit tracking

# PART 4 – MARKET & BUSINESS DOMAIN

This module manages

• Sell My Produce

• Market Prices

• Government Schemes

• Notifications

• Future Procurement

These modules connect farmers with buyers while keeping the farmer's experience simple.

--------------------------------------------------

RELATIONSHIP

Farmer

↓

Produce Listing

↓

Procurement

↓

Buyer (Future)

↓

Transaction (Future)

--------------------------------------------------

TABLE LIST

Produce

• produce_listings

• produce_images

• produce_status_history

• produce_views

Market

• market_locations

• market_prices

• market_price_history

Government

• government_schemes

• scheme_categories

• scheme_documents

• farmer_scheme_status

Notifications

• notifications

• notification_preferences

• notification_delivery_logs

Future

• buyers

• procurement_requests

• transactions

Total Tables

15

==================================================

TABLE : produce_listings

Purpose

Main produce listing table.

Fields

listing_id UUID

farmer_id UUID

farm_id UUID

crop_session_id UUID

crop_id UUID

quantity DECIMAL

unit

expected_price DECIMAL

currency

grade

harvest_date

available_from

available_until

description

status

is_active

created_at

updated_at

Status Values

Draft

Published

Looking for Buyer

Reserved

Sold

Cancelled

Indexes

farmer_id

crop_id

status

harvest_date

district

==================================================

TABLE : produce_images

Purpose

Store produce photographs.

Columns

image_id UUID

listing_id UUID

file_url

thumbnail_url

mime_type

uploaded_at

==================================================

TABLE : produce_status_history

Purpose

Track listing lifecycle.

Columns

history_id UUID

listing_id

old_status

new_status

changed_by

changed_at

==================================================

TABLE : produce_views

Purpose

Analytics.

Columns

view_id UUID

listing_id

viewer_type

viewer_id

viewed_at

==================================================

TABLE : market_locations

Purpose

Master list of markets.

Columns

market_id UUID

market_name

district

block

village

latitude

longitude

state

status

Indexes

district

market_name

==================================================

TABLE : market_prices

Purpose

Current market prices.

Columns

price_id UUID

market_id

crop_id

minimum_price

maximum_price

modal_price

unit

price_date

source

verified

Indexes

market_id

crop_id

price_date

==================================================

TABLE : market_price_history

Purpose

Historical prices.

Columns

history_id UUID

market_id

crop_id

price

unit

recorded_date

source

==================================================

TABLE : government_schemes

Purpose

Store verified government schemes.

Columns

scheme_id UUID

title

category

description

eligibility

benefits

application_process

official_url

state

department

start_date

end_date

status

verified_at

source

Important

Only verified schemes should be stored.

==================================================

TABLE : scheme_categories

Purpose

Master categories.

Examples

Insurance

Equipment

Subsidy

Loan

Seeds

Irrigation

Organic Farming

==================================================

TABLE : scheme_documents

Purpose

Required documents.

Columns

document_id UUID

scheme_id

document_name

is_required

==================================================

TABLE : farmer_scheme_status

Purpose

Track farmer applications.

Columns

status_id UUID

farmer_id

scheme_id

application_status

submitted_date

approved_date

remarks

==================================================

TABLE : notifications

Purpose

Main notification table.

Columns

notification_id UUID

farmer_id

category

title

message

priority

icon

action_url

is_read

created_at

Notification Categories

Weather

Disease

Government Scheme

Market Price

Reminder

AI Recommendation

Produce

General

Priority

Low

Medium

High

Critical

==================================================

TABLE : notification_preferences

Purpose

Notification settings.

Columns

preference_id UUID

farmer_id

weather_enabled

disease_enabled

market_enabled

scheme_enabled

produce_enabled

push_enabled

email_enabled

sms_enabled

voice_enabled

==================================================

TABLE : notification_delivery_logs

Purpose

Delivery history.

Columns

delivery_id UUID

notification_id

delivery_method

status

sent_at

delivered_at

opened_at

==================================================

TABLE : buyers (Future)

Purpose

Future buyer database.

Columns

buyer_id UUID

company_name

contact_person

phone

email

district

preferred_crops

status

==================================================

TABLE : procurement_requests (Future)

Purpose

Buyer requests.

Columns

request_id UUID

buyer_id

crop_id

required_quantity

required_date

status

==================================================

TABLE : transactions (Future)

Purpose

Future procurement transactions.

Columns

transaction_id UUID

listing_id

buyer_id

quantity

price

transaction_date

payment_status

==================================================

RELATIONSHIP SUMMARY

Farmer

↓

Produce Listing

↓

Produce Images

↓

Status History

↓

Future Buyer

↓

Transaction

--------------------------------------------------

MARKET FLOW

Government Market Data

↓

Market Price History

↓

Today's Price

↓

Farmer Dashboard

↓

AI Recommendation

--------------------------------------------------

NOTIFICATION FLOW

Weather

↓

AI

↓

Disease

↓

Government Scheme

↓

Market Price

↓

Notification Service

↓

Farmer

--------------------------------------------------

BUSINESS RULES

A produce listing must belong to one farmer.

A farmer may publish multiple listings.

Only verified government schemes should be shown.

Market prices must include source and update date.

Notifications are never permanently deleted.

All listing images must be stored in AWS S3.

Future buyer integration should not require schema redesign.

--------------------------------------------------

FUTURE FEATURES

Reserved support for

AI Quality Grading

Buyer Matching

Transport Scheduling

Cold Storage

Warehouse Allocation

Bulk Procurement

Digital Contracts

Payment Gateway

Invoice Generation

Supply Chain Analytics

# PART 5 – ADMINISTRATION, AUDIT & ANALYTICS DOMAIN

This module is responsible for

• Administration

• Audit Logging

• Analytics

• System Configuration

• AI Monitoring

• Security

• Performance

--------------------------------------------------

DATABASE MODULES

Administration

• admin_users

• admin_roles

• admin_permissions

• admin_activity_logs

Audit

• audit_logs

• change_history

Analytics

• analytics_events

• dashboard_metrics

• ai_usage_statistics

Configuration

• system_settings

• feature_flags

Monitoring

• api_logs

• error_logs

• ai_request_logs

• scheduled_jobs

Total Tables

14

==================================================

TABLE : admin_users

Purpose

Administrative users.

Columns

admin_id UUID

user_id UUID

role_id UUID

department

status

last_login

created_at

updated_at

==================================================

TABLE : admin_roles

Examples

Super Admin

Admin

Support

Content Manager

Agriculture Officer

Market Manager

Moderator

Columns

role_id UUID

role_name

description

==================================================

TABLE : admin_permissions

Examples

manage_users

manage_market_prices

manage_schemes

manage_notifications

view_analytics

manage_ai

Columns

permission_id UUID

permission_name

description

==================================================

TABLE : admin_activity_logs

Purpose

Track every admin action.

Columns

activity_id UUID

admin_id

action

resource_type

resource_id

old_value

new_value

ip_address

created_at

==================================================

TABLE : audit_logs

Purpose

Permanent system audit.

Columns

audit_id UUID

user_id

entity_type

entity_id

action

performed_by

device

ip_address

created_at

Examples

LOGIN

PROFILE_UPDATED

FARM_CREATED

DISEASE_ANALYZED

PRODUCE_PUBLISHED

==================================================

TABLE : change_history

Purpose

Track field-level changes.

Columns

change_id UUID

table_name

record_id

column_name

old_value

new_value

changed_by

changed_at

==================================================

TABLE : analytics_events

Purpose

Every user interaction.

Columns

event_id UUID

user_id

session_id

event_name

screen_name

device

platform

metadata JSONB

created_at

Examples

Open Home

Ask AI

Upload Disease Image

Open Weather

Publish Produce

==================================================

TABLE : dashboard_metrics

Purpose

Pre-calculated statistics.

Columns

metric_id UUID

metric_name

metric_value

calculated_at

Examples

Total Farmers

Active Farms

Disease Detections Today

Produce Listed

Weekly Active Users

==================================================

TABLE : ai_usage_statistics

Purpose

Track AI usage.

Columns

usage_id UUID

provider

model

request_count

success_count

failure_count

average_latency

average_tokens

total_cost

recorded_date

==================================================

TABLE : system_settings

Purpose

Application configuration.

Columns

setting_id UUID

setting_key

setting_value

description

updated_at

Examples

maintenance_mode

minimum_app_version

supported_languages

==================================================

TABLE : feature_flags

Purpose

Enable/disable features.

Columns

flag_id UUID

feature_name

enabled

rollout_percentage

created_at

Examples

Satellite Monitoring

Expert Connect

AI Yield Prediction

==================================================

TABLE : api_logs

Purpose

Track API performance.

Columns

log_id UUID

endpoint

method

status_code

duration_ms

request_size

response_size

created_at

==================================================

TABLE : error_logs

Purpose

Application errors.

Columns

error_id UUID

service

error_type

message

stack_trace

severity

resolved

created_at

==================================================

TABLE : ai_request_logs

Purpose

Monitor AI requests.

Columns

request_id UUID

provider

model

request_type

response_time

tokens_input

tokens_output

status

created_at

==================================================

TABLE : scheduled_jobs

Purpose

Background jobs.

Columns

job_id UUID

job_name

status

started_at

completed_at

duration

==================================================

INDEX STRATEGY

Every foreign key

Create Index

Frequently searched columns

Create Index

Dates

Create Index

Status fields

Create Index

Spatial fields

GiST Index

Search fields

GIN / Trigram Index

==================================================

CONSTRAINTS

Primary Keys

UUID

Unique Constraints

Firebase UID

Phone Number

Email

Check Constraints

Quantity > 0

Price >= 0

Confidence 0–100

Health Score 0–100

Foreign Keys

Every child table must reference parent table.

Cascade

Use carefully.

Prefer soft deletes.

==================================================

ER DIAGRAM

Users

↓

Farmer Profiles

↓

Farms

↓

Crop Sessions

├──────────────┐
│              │
▼              ▼

Disease      Weekly Growth

│              │

▼              ▼

Fertilizer   Weather

│              │

└──────┬───────┘
       ▼

AI Memory

       ▼

AI Conversations

       ▼

Recommendations

       ▼

Produce Listings

       ▼

Market

       ▼

Notifications

       ▼

Administration

==================================================

PERFORMANCE STRATEGY

Connection Pooling

Redis Cache

Pagination

Database Indexing

Lazy Loading

Image Storage in AWS S3

Background Workers

Optimized Queries

==================================================

SECURITY

Phone Authentication

JWT

HTTPS Only

Encrypted Secrets

Encrypted Sensitive Data

Audit Logs

Rate Limiting

Row-Level Authorization

==================================================

BACKUP

Daily Backup

Incremental Backup

Point-in-Time Recovery

Cross-Region Replication

==================================================

FUTURE MODULES

Reserved architecture for

Satellite Monitoring

Drone Analytics

IoT Sensors

AI Yield Prediction

Buyer Marketplace

Transport Management

Cold Storage

Insurance

Carbon Credits

Machine Rental

Warehouse Management

No redesign should be required to support these modules.

==================================================

DATABASE SUMMARY

Estimated Core Tables

Authentication               5

Farmer Profile               8

Farm                         8

Crop Intelligence           18

Market                       15

Administration              14

--------------------------------

Total Core Tables

Approximately 68 production-ready tables.

All tables use

• UUID Primary Keys

• Soft Deletes

• Audit Logging

• Created/Updated timestamps

• Foreign Keys

• Production-ready indexing

• AI-ready architecture

• PostgreSQL + PostGIS