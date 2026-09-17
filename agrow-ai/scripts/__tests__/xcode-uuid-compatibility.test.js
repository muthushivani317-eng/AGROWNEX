const xcode = require('xcode');

describe('patched Xcode UUID dependency', () => {
  it('still generates unique 24-character uppercase project identifiers', () => {
    const project = xcode.project('synthetic-project.pbxproj');
    project.hash = { project: { objects: {} } };
    const identifiers = new Set();
    for (let i = 0; i < 100; i += 1) {
      const id = project.generateUuid();
      expect(id).toMatch(/^[A-F0-9]{24}$/);
      identifiers.add(id);
    }
    expect(identifiers.size).toBe(100);
  });
});
