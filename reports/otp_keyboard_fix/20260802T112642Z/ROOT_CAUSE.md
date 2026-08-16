# Root cause

The original authoritative OTP `TextInput` was absolutely positioned at 1×1 pixels with opacity zero. That was an unreliable Android release IME target. The fix gives the native input a full-row, non-zero focus surface, makes IME/editability flags explicit, and schedules one bounded post-navigation focus with one retry.
