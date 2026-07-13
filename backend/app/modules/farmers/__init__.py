"""Farmer Profile module (docs/API_CONTRACT.md → FARMER MODULE).

Serves the farmer's own profile, preferences and language list. It reuses the
farmer_profiles / farmer_preferences / farmer_languages tables and models that
the authentication module already provisions — it never redefines those tables
and never touches identity/session logic.
"""
