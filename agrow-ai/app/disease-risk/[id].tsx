import { useLocalSearchParams } from "expo-router";
import { DiseaseRiskDetailScreen } from "@/features/diseaseRisk/DiseaseRiskDetailScreen";
export default function Route() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <DiseaseRiskDetailScreen id={typeof id === "string" ? id : ""} />;
}
