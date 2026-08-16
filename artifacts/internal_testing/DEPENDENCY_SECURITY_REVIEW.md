# Dependency security review

The two requested high-severity advisories are patched with compatible, in-range updates. No forced upgrade, Expo downgrade, or security-check suppression was used.

## brace-expansion — PATCHED

- Previous versions: `1.1.16`, `5.0.7`
- Installed/patched versions: `1.1.18`, `5.0.9`
- Vulnerable ranges: `<1.1.18`; `>=4.0.0 <5.0.9`
- Advisories: `GHSA-mh99-v99m-4gvg`, `GHSA-rgw5-rvv9-x895`
- Operation: attacker-controlled brace patterns can cause unbounded expansion and memory exhaustion.
- Reachability: Jest glob matching and Expo fingerprint/build tooling only. It is not imported into the shipped mobile runtime or APK JavaScript graph.
- Chains: Jest → glob → minimatch → brace-expansion; React Native Jest preset → Istanbul/test-exclude → minimatch → brace-expansion; Expo → fingerprint → minimatch → brace-expansion.

## postcss — PATCHED

- Previous version: `8.5.16`
- Installed version: `8.5.26`
- Patched range: `8.5.23` or later
- Vulnerable range: `<=8.5.22`
- Advisories: `GHSA-r28c-9q8g-f849`, `GHSA-fxqj-rqcc-2cmp`
- Operation: an attacker-controlled `sourceMappingURL` may cause unintended local source-map loading when processing untrusted CSS without a safe source filename.
- Reachability: trusted build-time CSS transformation through Tailwind/NativeWind and Expo Metro configuration. It is not present as an application runtime module in the APK.
- Chains: Tailwind and its PostCSS plugins → postcss; Expo → Metro configuration → postcss.

`npm update brace-expansion postcss` changed only compatible transitive versions (plus the patched `nanoid` dependency selected by npm). The subsequent native audit reports zero high and zero critical advisories; 13 moderate advisories remain for separate SDK-compatible triage.
