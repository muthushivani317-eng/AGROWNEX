/** Common Tamil Nadu crops with Tamil labels. Reused by profile, farm
 * registration, and market screens. */
export interface Crop {
  id: string;
  en: string;
  ta: string;
}

export const COMMON_CROPS: Crop[] = [
  { id: "paddy", en: "Paddy (Rice)", ta: "நெல்" },
  { id: "sugarcane", en: "Sugarcane", ta: "கரும்பு" },
  { id: "groundnut", en: "Groundnut", ta: "நிலக்கடலை" },
  { id: "cotton", en: "Cotton", ta: "பருத்தி" },
  { id: "maize", en: "Maize", ta: "மக்காச்சோளம்" },
  { id: "banana", en: "Banana", ta: "வாழை" },
  { id: "coconut", en: "Coconut", ta: "தென்னை" },
  { id: "tomato", en: "Tomato", ta: "தக்காளி" },
  { id: "brinjal", en: "Brinjal", ta: "கத்தரிக்காய்" },
  { id: "chilli", en: "Chilli", ta: "மிளகாய்" },
  { id: "turmeric", en: "Turmeric", ta: "மஞ்சள்" },
  { id: "millet", en: "Millet", ta: "சிறுதானியம்" },
  { id: "redgram", en: "Redgram", ta: "துவரை" },
  { id: "blackgram", en: "Black gram", ta: "உளுந்து" },
  { id: "pearl_millet", en: "Pearl millet", ta: "கம்பு" },
  { id: "greengram", en: "Green gram", ta: "பாசிப்பயறு" },
];

/** Crops currently supported by the general Disease Detection model.
 * Preferred-crop pickers use this exact list so a farmer can select every
 * crop they can later diagnose. */
export const DISEASE_DETECTION_CROP_IDS = [
  "banana",
  "chilli",
  "redgram",
  "paddy",
  "cotton",
  "groundnut",
  "coconut",
  "blackgram",
  "maize",
  "pearl_millet",
  "greengram",
] as const;

export const DISEASE_DETECTION_CROPS: Crop[] = DISEASE_DETECTION_CROP_IDS.map(
  (id) => COMMON_CROPS.find((crop) => crop.id === id)!,
);
