export type FallbackCardId = "patient-banner" | "severity" | "labs" | "cxr" | "summary";

/**
 * Maps data_gaps strings from the pipeline to the dashboard card they affect.
 * Returns the matching gap strings for the given card so they can be shown in a tooltip.
 */
export function getCardFallbacks(dataGaps: string[] | undefined, card: FallbackCardId): string[] {
  if (!dataGaps || dataGaps.length === 0) return [];

  return dataGaps.filter((gap) => {
    const lower = gap.toLowerCase();
    switch (card) {
      case "patient-banner":
        return lower.includes("demographics from case data") || lower.includes("clinical exam from case data");
      case "severity":
        return lower.includes("curb-65 variables from case data");
      case "labs":
        return lower.includes("lab") && !lower.includes("variables");
      case "cxr":
        return lower.includes("cxr") || lower.includes("chest");
      case "summary":
        return lower.includes("deterministic fallback");
      default:
        return false;
    }
  });
}
