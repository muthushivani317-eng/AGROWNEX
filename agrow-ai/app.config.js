const {
  loadPublicEnvironment,
  validateBuildEnvironment,
} = require("./scripts/validate-release-env");

const publicEnvironment = loadPublicEnvironment(__dirname);
const buildValidation = validateBuildEnvironment(publicEnvironment);
const isProductionSecurity = buildValidation.productionSecurityEnforced;
const isControlledTesting =
  buildValidation.profile === "internal_testing" ||
  buildValidation.profile === "kvk_field_test";

module.exports = {
  expo: {
    name: "AgrowNex",
    slug: "agrow-ai",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/images/icon.png",
    scheme: "agrowai",
    userInterfaceStyle: "automatic",
    newArchEnabled: true,
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.agrowai.app",
      infoPlist: {
        NSLocationWhenInUseUsageDescription:
          "AgrowAI uses your location to show local weather, market prices, and to locate your farms.",
        NSCameraUsageDescription:
          "AgrowAI uses the camera to scan crops for disease detection.",
        NSPhotoLibraryUsageDescription:
          "AgrowAI needs access to your photos to upload crop and produce images.",
      },
    },
    android: {
      package: "com.agrowai.app",
      softwareKeyboardLayoutMode: "resize",
      allowBackup: false,
      googleServicesFile:
        process.env.GOOGLE_SERVICES_JSON ?? "./google-services.json",
      adaptiveIcon: {
        backgroundColor: "#FFFFFF",
        foregroundImage: "./assets/images/android-icon-foreground.png",
        backgroundImage: "./assets/images/android-icon-background.png",
        monochromeImage: "./assets/images/android-icon-monochrome.png",
      },
      permissions: [
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.CAMERA",
      ],
      predictiveBackGestureEnabled: false,
    },
    web: {
      bundler: "metro",
      output: "static",
      favicon: "./assets/images/favicon.png",
    },
    plugins: [
      "expo-asset",
      "./plugins/withReleaseEnvironmentValidation",
      "./plugins/withProductionSigning",
      "@react-native-firebase/app",
      "@react-native-firebase/crashlytics",
      "expo-router",
      "expo-secure-store",
      "expo-localization",
      "expo-image",
      "expo-font",
      [
        "expo-build-properties",
        {
          android: {
            usesCleartextTraffic: !isProductionSecurity,
          },
        },
      ],
      [
        "expo-splash-screen",
        {
          // Android 12+ displays this as a centered splash icon. A full
          // portrait poster is cropped into a rounded square, so keep the
          // native layer to the standalone transparent AgrowAI emblem. The
          // richer bilingual composition is rendered by SplashScreen.tsx.
          image: "./assets/images/android-icon-foreground.png",
          imageWidth: 180,
          resizeMode: "contain",
          backgroundColor: "#FBF7EA",
        },
      ],
      [
        "expo-location",
        {
          locationWhenInUsePermission:
            "AgrowAI uses your location to show local weather, market prices, and to locate your farms.",
        },
      ],
      [
        "expo-image-picker",
        {
          photosPermission:
            "AgrowAI needs access to your photos to upload crop and produce images.",
          cameraPermission:
            "AgrowAI uses the camera to scan crops for disease detection.",
        },
      ],
      [
        "expo-audio",
        {
          microphonePermission:
            "AgrowAI uses your microphone to record short voice notes about your farm tasks.",
          enableBackgroundPlayback: false,
        },
      ],
      "expo-sqlite",
    ],
    experiments: { typedRoutes: true },
    extra: {
      router: {},
      buildProfile: buildValidation.profile,
      releaseChannel: buildValidation.profile,
      internalTesting: {
        enabled: isControlledTesting,
        allTestableFeatures: isControlledTesting,
        developerMocks: false,
        productionAuth: isControlledTesting,
        productionApi: isControlledTesting,
      },
      eas: { projectId: "bc221c53-98f9-48f8-af0d-44bbf3fa1611" },
    },
  },
};
