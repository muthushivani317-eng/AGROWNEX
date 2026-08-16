# Route audit

All resolved destinations exist in the Expo Router tree:

- Fresh/no language: `/(auth)/language`
- Language selected, onboarding incomplete: `/(auth)/onboarding`
- Language selected and logged out: `/(auth)/login`
- Authenticated, incomplete profile: `/(auth)/complete-profile`
- Authenticated, complete profile: `/(tabs)`

`app/index.tsx` no longer performs a competing redirect or renders `null`. `useStartupRouteGuard` is the only startup redirect controller and refuses unknown target routes by construction through a closed route union.

The main route exists at `app/(tabs)/index.tsx`. Its quick actions expose Disease Detection, Weather, Crop Calendar, Market Prices, Government Schemes, Sell Produce, Notifications, AI Assistant, Plant Identifier, Add Farm, Growth Monitor, and Soil Intelligence. Existing crop capability guards remain responsible for unreleased runtime access.
