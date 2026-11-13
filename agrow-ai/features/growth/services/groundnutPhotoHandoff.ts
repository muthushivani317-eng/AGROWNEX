import type { PickedImage } from "@/features/disease";

let pendingPhoto: PickedImage | null = null;

/** One-time, in-memory handoff from confirmed Groundnut crop ID to Growth Monitor. */
export function setGroundnutGrowthPhoto(photo: PickedImage): void {
  pendingPhoto = { ...photo };
}

export function consumeGroundnutGrowthPhoto(): PickedImage | null {
  const photo = pendingPhoto;
  pendingPhoto = null;
  return photo;
}
