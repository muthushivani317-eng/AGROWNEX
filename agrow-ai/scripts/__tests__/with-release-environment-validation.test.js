const {
  injectReleaseValidation,
} = require('../../plugins/withReleaseEnvironmentValidation');

describe('release validation config plugin', () => {
  it('creates and wires the validator into release build lifecycle tasks', () => {
    const result = injectReleaseValidation('apply plugin: "com.android.application"\n');
    expect(result).toContain('tasks.register("validateReleaseEnvironment", Exec)');
    expect(result).toContain('task.name == "preReleaseBuild"');
    expect(result).toContain('task.name == "bundleRelease"');
    expect(result).toContain('task.dependsOn tasks.named("validateReleaseEnvironment")');
  });

  it('is idempotent across repeated Expo prebuild evaluation', () => {
    const once = injectReleaseValidation('android {}\n');
    const twice = injectReleaseValidation(once);
    expect(twice).toBe(once);
    expect((twice.match(/tasks\.register\("validateReleaseEnvironment"/g) || []).length).toBe(1);
  });
});
