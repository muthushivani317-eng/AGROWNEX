export const internalSafetyMessages = {
  checking: { ta: 'படம் சரிபார்க்கப்படுகிறது', en: 'Checking the image' },
  lowQuality: { ta: 'படத்தின் தரம் குறைவாக உள்ளது', en: 'The image quality is too low' },
  nonPlant: { ta: 'தாவரம் கண்டறியப்படவில்லை', en: 'No plant was detected' },
  unsupported: { ta: 'ஆதரிக்கப்படாத பயிர்', en: 'This crop is not supported' },
  uncertain: { ta: 'பயிரை உறுதியாக கண்டறிய முடியவில்லை', en: 'The crop could not be identified reliably' },
  confirm: { ta: 'கண்டறியப்பட்ட பயிரை உறுதிப்படுத்தவும்', en: 'Confirm the identified crop' },
  correct: { ta: 'வேறு பயிரைத் தேர்ந்தெடுக்கவும்', en: 'Choose a different crop' },
  retry: { ta: 'மீண்டும் படம் எடுக்கவும்', en: 'Take another photo' },
  unavailable: { ta: 'சேவை தற்காலிகமாக கிடைக்கவில்லை', en: 'The service is temporarily unavailable' },
  restricted: {
    ta: 'இந்த பயிருக்கு நோய் மாதிரி தற்போது கட்டுப்படுத்தப்பட்டுள்ளது',
    en: 'The disease model for this crop is currently restricted',
  },
} as const;

export function messageForInternalReason(reason: string) {
  if (reason === 'LOW_QUALITY') return internalSafetyMessages.lowQuality;
  if (reason === 'NON_PLANT') return internalSafetyMessages.nonPlant;
  if (reason === 'UNSUPPORTED_CROP') return internalSafetyMessages.unsupported;
  if (reason === 'RUNTIME_UNAVAILABLE' || reason === 'RUNTIME_INTEGRITY_FAILURE') return internalSafetyMessages.unavailable;
  if (reason === 'DISEASE_RUNTIME_RESTRICTED') return internalSafetyMessages.restricted;
  return internalSafetyMessages.uncertain;
}
