/** Layout-only grouping; preserves commas inside parenthesized amounts. */
export function splitSchemeBenefits(text: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let start = 0;
  for (let index = 0; index < text.length; index++) {
    if (text[index] === "(") depth++;
    else if (text[index] === ")") depth = Math.max(0, depth - 1);
    else if (
      text[index] === "," &&
      depth === 0 &&
      !(/\d/.test(text[index - 1] ?? "") && /\d/.test(text[index + 1] ?? ""))
    ) {
      parts.push(text.slice(start, index).trim());
      start = index + 1;
    }
  }
  parts.push(text.slice(start).trim());
  return parts.filter(Boolean);
}
