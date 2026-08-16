# Release environment validation

The removed native task was recovered from
`agrow-ai/android.backup-before-standalone-20260801-185713/app/build.gradle`.
It executed `scripts/validate-release-env.js` and was a dependency of
`preReleaseBuild`.

The repair uses the Expo config plugin
`plugins/withReleaseEnvironmentValidation.js`. A clean Expo prebuild regenerated
Android and restored `:app:validateReleaseEnvironment`; both `preReleaseBuild`
and `bundleRelease` depend on it. This makes the guard reproducible across future
prebuilds.

Production validation requires the production profile, the exact HTTPS API path
`/api/v1`, an HTTPS diagnosis origin with root path, public DNS hostnames, and
required Firebase public configuration. Localhost, loopback, emulator, private
IPv4, `.local`, `.lan`, `.internal`, `.test`, single-label development hosts,
credentials, query strings, fragments, and non-443 explicit ports fail closed.

The configured Railway URLs passed. Direct Gradle validation finished with
`BUILD SUCCESSFUL`. Focused tests: 21/21 passed.
