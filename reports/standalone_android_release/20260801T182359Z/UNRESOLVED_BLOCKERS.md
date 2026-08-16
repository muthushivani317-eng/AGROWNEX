# Unresolved blockers

1. Connect and authorize the Android device in ADB.
2. Install and directly launch the generated APK.
3. Confirm no Dev Launcher UI and capture launch logs.
4. Supply an authorized Firebase test phone number manually; do not record it in
   reports.
5. Complete OTP request, manual verification, invalid-OTP, Railway token exchange,
   and post-login checks.
6. Complete the laptop-off reopen and safe authenticated API request.
7. Replace debug signing with protected production signing before distribution.
8. Decide whether the strict forbidden-literal policy should exempt documented
   framework strings; active API endpoints already pass the fail-closed validator.
9. Triage and resolve or formally accept the production dependency audit's two
   high build/tooling advisories before farmer release. No forced or major-version
   downgrade remediation was applied.
