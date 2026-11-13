export const GROUNDNUT_CLASS_INFORMATION: Record<
  string,
  { title: string; description: string }
> = {
  early_leaf_spot: {
    title: "Early Leaf Spot",
    description:
      "An experimental model class for possible early leaf spot. Confirm visible symptoms with a KVK or agriculture officer before taking action.",
  },
  healthy_leaf: {
    title: "Healthy Leaf",
    description:
      "The model did not identify one of its four known problem classes. This does not rule out other diseases, pests, or crop stress.",
  },
  late_leaf_spot: {
    title: "Late Leaf Spot",
    description:
      "An experimental model class for possible late leaf spot. Expert confirmation is needed before treatment decisions.",
  },
  nutrition_deficiency: {
    title: "Nutrition Deficiency",
    description:
      "The photograph may resemble the model's nutrition-deficiency class. A photograph alone cannot identify the deficient nutrient; use field and soil assessment.",
  },
  rust: {
    title: "Rust",
    description:
      "An experimental model class for possible Groundnut rust. Confirm the signs with a KVK or agriculture officer before treatment decisions.",
  },
};
