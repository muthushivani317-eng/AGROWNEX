# APK static inspection

- Package: `com.agrowai.app`; version `1.0.0` (1).
- Launcher: `com.agrowai.app.MainActivity` only.
- Application label: `AgrowAI`.
- Embedded bundle: `assets/index.android.bundle`.
- Internet permission: present.
- Cleartext traffic: disabled.
- Firebase Auth registrar, Firebase init providers, and generated Firebase string
  resource names are present. Values were not printed.
- `expo-dev-client`, `expo-dev-launcher`, `expo-dev-menu`, Expo Dev Launcher
  activity, and Dev Launcher UI phrases were not found.
- Both configured Railway HTTPS URLs are present in the embedded bundle.

Generic `localhost`, `127.0.0.1`, `10.0.2.2`, and `192.168.` text occurs in
framework/dependency code and resources. Inspected bundle context attributes
these to Firebase Android emulator remapping, React Native/Expo development
diagnostics, font asset packager placeholders, and validation code—not to the
active AgrowAI API configuration. Therefore the strict literal-absence check is
not satisfied, although the active public environment is independently bound to
the Railway HTTPS URLs and the release validator rejects those hosts.

Signing uses the Android debug certificate for direct internal installation.
This APK is not signed for store/production distribution.
