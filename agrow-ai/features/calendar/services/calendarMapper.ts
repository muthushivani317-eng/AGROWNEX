import type {
  ApiCalendarEvent,
  ApiCalendarSummary,
  CalendarEvent,
  CalendarSummary,
} from "../types";

export function apiToEvent(dto: ApiCalendarEvent): CalendarEvent {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    crop: dto.crop,
    season: dto.season,
    code: dto.code,
    activityType: dto.activity_type,
    title: dto.title,
    description: dto.description,
    scheduledDate: dto.scheduled_date,
    dayOffset: dto.day_offset,
    growthStage: dto.growth_stage,
    priority: dto.priority,
    status: dto.status,
    weatherDependency: dto.weather_dependency,
    weatherAdvisory: dto.weather_advisory ?? "none",
    reminderEnabled: dto.reminder_enabled,
    reminderHour: dto.reminder_hour,
    completedAt: dto.completed_at,
    notes: dto.notes,
    registryVersion: dto.registry_version,
    registryVerificationStatus: dto.registry_verification_status,
    registrySourceReference: dto.registry_source_reference,
    isOrganic: dto.is_organic === true,
    createdAt: dto.created_at,
    dataState: "live",
    cachedAt: null,
  };
}

export function apiToSummary(dto: ApiCalendarSummary): CalendarSummary {
  return {
    farmId: dto.farm_id,
    crop: dto.crop,
    season: dto.season,
    total: dto.total,
    completed: dto.completed,
    pending: dto.pending,
    missed: dto.missed,
    skipped: dto.skipped,
  };
}
