import type { PickedImage } from "@/features/disease";

import {
  consumeGroundnutGrowthPhoto,
  setGroundnutGrowthPhoto,
} from "../services/groundnutPhotoHandoff";

test("hands a confirmed Groundnut photo to Growth Monitor exactly once", () => {
  const photo: PickedImage = {
    uri: "file://groundnut.jpg",
    base64: "",
    mimeType: "image/jpeg",
    width: 1000,
    height: 1000,
    fileSize: 100_000,
  };

  setGroundnutGrowthPhoto(photo);

  expect(consumeGroundnutGrowthPhoto()).toEqual(photo);
  expect(consumeGroundnutGrowthPhoto()).toBeNull();
});
