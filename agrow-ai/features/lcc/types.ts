export type LccStatus = "deficient" | "borderline" | "sufficient" | "abstained";

export interface LccResult {
  farm_id: string;
  crop: string | null;
  abstained: boolean;
  quality_issue: string | null;
  panel_number: number | null;
  nitrogen_status: LccStatus;
  guidance_key: string;
  average_lab: [number, number, number] | null;
  color_distance: number | null;
  leaf_pixel_ratio: number;
  brightness: number;
  sharpness: number;
  method: "cie76";
  is_estimate: true;
}
