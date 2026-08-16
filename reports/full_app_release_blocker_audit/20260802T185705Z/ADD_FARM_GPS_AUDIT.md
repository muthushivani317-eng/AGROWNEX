# Add Farm and GPS Audit

Implemented/confirmed:

- prominent `Use my location` action;
- permission request via Expo Location;
- loading state;
- explicit permission-denied/unavailable card with Retry;
- precise coordinates removed from the screen and logs;
- styled map controls and visible area calculation already exist;
- missing date translation key repaired;
- status uses chips;
- disabled submit now explains the minimum required fields.

Not proven on device: permission dialog, GPS-disabled/timeout differentiation, current-location map recentering, boundary interaction and real backend farm submission. Result: `PARTIAL_PHYSICAL_VALIDATION_REQUIRED`.
