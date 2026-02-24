import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import type { CURB65Score } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface CURB65RadarProps {
  score: CURB65Score | null;
}

const SEVERITY_COLORS: Record<string, string> = {
  low: "oklch(0.72 0.19 142)",
  moderate: "oklch(0.75 0.18 75)",
  high: "oklch(0.63 0.24 25)",
};

function CustomAxisTick({
  payload,
  x,
  y,
  cx,
  cy,
  dataEntry,
}: {
  payload: { value: string };
  x: number;
  y: number;
  cx: number;
  cy: number;
  dataEntry?: { value: number };
}) {
  const isPositive = (dataEntry?.value ?? 0) >= 1;
  const fill = isPositive
    ? "oklch(0.63 0.24 25)" // red
    : "oklch(0.72 0.19 142)"; // green

  // Offset text away from center
  const dx = x - cx;
  const dy = y - cy;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const offsetX = dist > 0 ? (dx / dist) * 12 : 0;
  const offsetY = dist > 0 ? (dy / dist) * 12 : 0;

  return (
    <text
      x={x + offsetX}
      y={y + offsetY}
      textAnchor="middle"
      dominantBaseline="central"
      fill={fill}
      fontSize={11}
      fontFamily="JetBrains Mono, monospace"
      fontWeight={isPositive ? 700 : 400}
    >
      {payload.value}
    </text>
  );
}

export function CURB65Radar({ score }: CURB65RadarProps) {
  if (!score) {
    return (
      <Card className="border-border/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">CURB-65 Components</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-36 text-xs text-muted-foreground">
          No CURB-65 data
        </CardContent>
      </Card>
    );
  }

  // Map 0 → 0.2 so the shape is always visible
  const mapValue = (v: number) => (v === 0 ? 0.2 : v);

  const data = [
    { axis: "Confusion", value: mapValue(score.c), refValue: 1 },
    { axis: "Urea >7", value: mapValue(score.u), refValue: 1 },
    { axis: "RR ≥30", value: mapValue(score.r), refValue: 1 },
    { axis: "BP", value: mapValue(score.b), refValue: 1 },
    { axis: "Age ≥65", value: mapValue(score.age_65), refValue: 1 },
  ];

  const color = SEVERITY_COLORS[score.severity_tier] ?? SEVERITY_COLORS.moderate;

  return (
    <Card className="border-border/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          CURB-65 Components
          <span className="text-lg font-bold font-mono" style={{ color }}>
            {score.curb65 ?? score.crb65}/5 ({score.severity_tier})
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="65%">
            <PolarGrid stroke="var(--border)" opacity={0.3} />
            <PolarAngleAxis
              dataKey="axis"
              tick={(props: Record<string, unknown>) => {
                const index = props.index as number;
                const entry = data[index];
                return (
                  <CustomAxisTick
                    {...(props as { payload: { value: string }; x: number; y: number; cx: number; cy: number })}
                    dataEntry={entry}
                  />
                );
              }}
            />
            <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
            {/* Reference outline at max */}
            <Radar
              name="Reference"
              dataKey="refValue"
              stroke="var(--muted-foreground)"
              fill="none"
              strokeWidth={1}
              strokeDasharray="4 3"
              strokeOpacity={0.15}
            />
            {/* Actual score */}
            <Radar
              name="CURB-65"
              dataKey="value"
              stroke={color}
              fill={color}
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
