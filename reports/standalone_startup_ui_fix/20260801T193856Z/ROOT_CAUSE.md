# Root cause

The release mounted two splash layers in sequence. Android first rendered the configured native `expo-splash-screen` artwork. `app/_layout.tsx` then mounted the React `features/auth/screens/SplashScreen.tsx` overlay using the same artwork.

The React overlay had two independent defects: image dimensions depended on NativeWind class processing, producing the observed small centered image on the device, and its fade animated only the inner view while the absolute black outer overlay remained mounted until a Reanimated completion callback. If that callback did not complete in release, the opaque overlay covered the route tree indefinitely.

Startup also had competing redirects in `app/index.tsx` and the root route guard, while both files could render `null` during initialization. Initialization errors were logged and then treated as ready, making a blank route/overlay possible without a fatal exception.

The fix removes the React splash from the mounted startup path, centralizes route resolution, always renders a visible startup state, bounds startup to 15 seconds, and supplies a recoverable error screen.
