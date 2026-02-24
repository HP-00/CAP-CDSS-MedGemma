/** Traffic-light severity mapping for clinical UI. */

export type SeverityTier = "low" | "moderate" | "high";

const SEVERITY_CONFIG: Record<
  SeverityTier,
  {
    bg: string;
    text: string;
    border: string;
    badge: string;
    glow: string;
    label: string;
  }
> = {
  low: {
    bg: "bg-severity-low/10",
    text: "text-severity-low",
    border: "border-severity-low/30",
    badge: "bg-severity-low/20 text-severity-low border-severity-low/30",
    glow: "glow-severity-low",
    label: "Low Risk",
  },
  moderate: {
    bg: "bg-severity-moderate/10",
    text: "text-severity-moderate",
    border: "border-severity-moderate/30",
    badge:
      "bg-severity-moderate/20 text-severity-moderate border-severity-moderate/30",
    glow: "glow-severity-moderate",
    label: "Moderate Risk",
  },
  high: {
    bg: "bg-severity-high/10",
    text: "text-severity-high",
    border: "border-severity-high/30",
    badge: "bg-severity-high/20 text-severity-high border-severity-high/30",
    glow: "glow-severity-high",
    label: "High Risk",
  },
};

export function getSeverityConfig(tier: SeverityTier) {
  return SEVERITY_CONFIG[tier] ?? SEVERITY_CONFIG.moderate;
}

export function getConfidenceColor(confidence: string): string {
  switch (confidence) {
    case "high":
      return "text-severity-high";
    case "moderate":
      return "text-severity-moderate";
    case "low":
      return "text-muted-foreground";
    default:
      return "text-muted-foreground";
  }
}
