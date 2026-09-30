import fs from 'node:fs';
import path from 'node:path';

test('daily task empty state uses a readable Home surface without a text background block', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../../dailyFarmTask/components/DailyFarmTaskCard.tsx'), 'utf8');
  expect(source).toContain('center color="inherit" style={styles.emptyText}');
  expect(source).toContain("backgroundColor: '#FFFDF8'");
  expect(source).toContain("borderColor: '#DED9CA'");
  expect(source).toContain("color: '#4F6057'");
  expect(source).toContain("backgroundColor: 'transparent'");
  expect(source).toContain('t("dailyTask.emptyState")');
  expect(source).toContain('<TaskResponseSheet');
  expect(source).toContain('localizedTaskText(task, isTamil, t)');
  expect(source).toContain('style={[styles.taskText, { color: colors.text }]}');
  expect(source).not.toContain('numberOfLines={2}');
  expect(source).toContain("backgroundColor: '#FFFDF8'");
  expect(source).toContain("borderColor: '#DED9CA'");
  expect(source).toContain('event.stopPropagation()');
  expect(source).toContain('style={styles.audioButton}');
  expect(source).not.toContain('{task.task_text_ta}');
});
