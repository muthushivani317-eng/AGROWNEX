# Root cause

The real-device UI hierarchy is the primary evidence. It contains the native Android content container and React Native `ViewGroup` tree at full device bounds, but the routed React child is invisible with bounds `[0,0][1080,0]`. No language text or controls exist in that hierarchy.

The release route resolver correctly selected `/(auth)/language`; the failure was rendering, not routing. Critical layout height depended exclusively on NativeWind `className="flex-1"` at the root navigator, root content wrapper, and `AgScreen`. On this release/device path that style was not applied to the routed child, collapsing it to zero height. The native splash then exposed an empty dark activity.

The supplied `after-repair-screen.png` is not a valid PNG: its bytes were UTF-16 transformed (`FF FE EB 00 50 00 4E 00 47...`) during an earlier PowerShell capture. It is preserved unchanged as `BEFORE_SCREENSHOT.png`, but no pixel claim is based on it.

The correction adds native React Native `style` fallbacks for critical root, screen, text, and primary-action geometry while retaining NativeWind decoration. It also registers `/(auth)/otp`, removes onboarding from the required fresh-login decision path, and resets the route guard's navigation lock after reaching a target.
