import { normalizeIndianPhone, sanitizeIndianPhoneInput } from "../phone";
import {
  authAvailabilityMessageKey,
  selectAuthProvider,
} from "../services/authProvider";
import { firebaseAuthProvider } from "../services/firebaseAuthProvider";
import { mockAuthProvider } from "../services/mockAuthProvider";

const mockConfirm = jest.fn();
const mockSignInWithPhoneNumber = jest.fn();
const mockGetIdTokenResult = jest.fn();

jest.mock("@/lib/firebase", () => ({ getFirebaseAuth: jest.fn(() => ({})) }));
jest.mock("@react-native-firebase/auth", () => ({
  AppleAuthProvider: { credential: jest.fn() },
  GoogleAuthProvider: { credential: jest.fn() },
  getIdTokenResult: (...args: unknown[]) => mockGetIdTokenResult(...args),
  signInWithCredential: jest.fn(),
  signInWithPhoneNumber: (...args: unknown[]) =>
    mockSignInWithPhoneNumber(...args),
  signOut: jest.fn(),
}));

describe("Firebase phone production safety", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignInWithPhoneNumber.mockResolvedValue({ confirm: mockConfirm });
  });

  it.each([
    ["9876543210", "+919876543210"],
    ["+91 98765 43210", "+919876543210"],
    ["(98765) 43210", "+919876543210"],
  ])("normalizes %s to E.164", (input, expected) => {
    expect(normalizeIndianPhone(input)).toBe(expected);
  });

  it.each([
    ["9876543210", "9876543210"],
    ["+91 98765 43210", "9876543210"],
    ["98a76-543 210", "9876543210"],
    ["987654321099", "9876543210"],
  ])(
    "sanitizes pasted field input %s without exposing a prefix in the field",
    (input, expected) => {
      expect(sanitizeIndianPhoneInput(input)).toBe(expected);
    },
  );

  it.each(["12345", "+91987654321", "+929876543210", "5876543210"])(
    "rejects invalid Indian phone %s",
    (input) =>
      expect(() => normalizeIndianPhone(input)).toThrow("auth.invalidPhone"),
  );

  it("fails closed instead of selecting mock auth in production", async () => {
    const provider = selectAuthProvider(false, "production");
    expect(provider).not.toBe(mockAuthProvider);
    await expect(provider.sendOtp("+919876543210")).rejects.toMatchObject({
      code: "auth/firebase-not-configured",
    });
  });

  it.each(["000000", "123456"])(
    "cannot use fixed code %s when Firebase is unavailable in internal testing",
    async (code) => {
      const provider = selectAuthProvider(false, "internal_testing");
      expect(provider).not.toBe(mockAuthProvider);
      await expect(provider.sendOtp("+919876543210")).rejects.toMatchObject({
        code: "auth/firebase-not-configured",
      });
      expect(code).toHaveLength(6);
    },
  );

  it("blocks test login and reports Firebase unavailable in the KVK field build", async () => {
    const provider = selectAuthProvider(false, "kvk_field_test");
    expect(provider).not.toBe(mockAuthProvider);
    expect(authAvailabilityMessageKey(false, "kvk_field_test")).toBe(
      "auth.otpVerificationUnavailable",
    );
    await expect(provider.sendOtp("+919876543210")).rejects.toMatchObject({
      code: "auth/firebase-not-configured",
    });
  });

  it("labels mock verification only in an explicit development profile", () => {
    expect(authAvailabilityMessageKey(false, "development")).toBe(
      "auth.devHint",
    );
    expect(authAvailabilityMessageKey(true, "kvk_field_test")).toBeNull();
  });

  it("allows the mock only in an explicit non-production profile", () => {
    expect(selectAuthProvider(false, "development")).toBe(mockAuthProvider);
  });

  it("maps an expired confirmation without accepting it", async () => {
    mockConfirm.mockRejectedValue({ code: "auth/session-expired" });
    const confirmation = await firebaseAuthProvider.sendOtp("+919876543210");
    await expect(confirmation.confirm("123456")).rejects.toMatchObject({
      code: "auth/session-expired",
      message: "auth.otpCodeExpired",
    });
  });

  it("requires a Firebase ID token before returning a credential", async () => {
    const user = {
      uid: "uid",
      phoneNumber: null,
      email: null,
      displayName: null,
      photoURL: null,
    };
    mockConfirm.mockResolvedValue({ user });
    mockGetIdTokenResult.mockRejectedValue({ code: "auth/user-token-expired" });
    const confirmation = await firebaseAuthProvider.sendOtp("+919876543210");
    await expect(confirmation.confirm("123456")).rejects.toMatchObject({
      code: "auth/user-token-expired",
    });
  });
});
