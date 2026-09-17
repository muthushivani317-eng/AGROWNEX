import { en } from "@/localization/locales/en";
import { ta } from "@/localization/locales/ta";

it("keeps conflict, expiry, and evidence-deferral copy in English and Tamil", () => {
  for (const locale of [en, ta]) {
    expect(locale.actionVerification.conflictTitle).toBeTruthy();
    expect(locale.actionVerification.conflictMessage).toBeTruthy();
    expect(locale.actionVerification.keepServer).toBeTruthy();
    expect(locale.actionVerification.applyMine).toBeTruthy();
    expect(locale.actionVerification.evidenceUnavailable).toBeTruthy();
    expect(locale.actionVerification.status.expired).toBeTruthy();
    expect(locale.actionVerification.status.unable_to_complete).toBeTruthy();
  }
});
