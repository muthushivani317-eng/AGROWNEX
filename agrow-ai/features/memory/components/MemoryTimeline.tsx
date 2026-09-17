import { StyleSheet, View } from "react-native";
import type { FarmMemory } from "../types";
import { MemoryCard } from "./MemoryCard";

export function MemoryTimeline({
  memories,
  onSelect,
}: {
  memories: FarmMemory[];
  onSelect?: (m: FarmMemory) => void;
}) {
  return (
    <View style={styles.list}>
      {memories.map((memory) => (
        <MemoryCard
          key={memory.id}
          memory={memory}
          onPress={onSelect ? () => onSelect(memory) : undefined}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({ list: { gap: 12 } });
