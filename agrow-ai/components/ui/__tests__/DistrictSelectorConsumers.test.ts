import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..", "..", "..");
const consumers = [
  "features/auth/screens/CompleteProfileScreen.tsx",
  "features/profile/screens/EditProfileScreen.tsx",
  "features/farm/screens/FarmFormScreen.tsx",
];

test.each(consumers)("%s uses the shared district selector", (relativePath) => {
  const source = fs.readFileSync(path.join(root, relativePath), "utf8");
  expect(source).toContain("AgDistrictDropdown");
  expect(source).not.toContain("districtOptions");
});

test.each(consumers)(
  "%s clears dependent locality fields when district changes",
  (relativePath) => {
    const source = fs.readFileSync(path.join(root, relativePath), "utf8");
    expect(source).toMatch(
      /setValue\(["']block["'], ["']["'], \{ shouldDirty: true \}\)/,
    );
    expect(source).toMatch(
      /setValue\(["']village["'], ["']["'], \{ shouldDirty: true \}\)/,
    );
  },
);
