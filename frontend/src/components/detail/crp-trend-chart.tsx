import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ReferenceArea,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { MonitoringPlan } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface CRPTrendChartProps {
  monitoringPlan: MonitoringPlan | null;
}

export function CRPTrendChart({ monitoringPlan }: CRPTrendChartProps) {
  const crpTrend = monitoringPlan?.crp_trend;

  if (!crpTrend) {
    return (
      <Card className="border-border/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">CRP Trend</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-36 text-xs text-muted-foreground">
          Insufficient temporal data
        </CardContent>
      </Card>
    );
  }

  const data = [
    { time: "Admission", crp: crpTrend.admission_value },
    { time: "Current", crp: crpTrend.current_value },
  ];

  const maxCrp = Math.max(crpTrend.admission_value, crpTrend.current_value, 20);
  const yMax = Math.ceil(maxCrp / 50) * 50 + 50;

  return (
    <Card className="border-border/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          CRP Trend
          <span className={`text-[11px] font-mono ${
            crpTrend.trend === "improving"
              ? "text-severity-low"
              : crpTrend.trend === "worsening"
                ? "text-severity-high"
                : "text-severity-moderate"
          }`}>
            {crpTrend.percent_change >= 0 ? "+" : ""}{crpTrend.percent_change.toFixed(0)}% ({crpTrend.trend})
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
            {/* Color zones */}
            <ReferenceArea y1={0} y2={10} fill="oklch(0.72 0.19 142)" fillOpacity={0.05} />
            <ReferenceArea y1={10} y2={100} fill="oklch(0.75 0.18 75)" fillOpacity={0.05} />
            <ReferenceArea y1={100} y2={yMax} fill="oklch(0.63 0.24 25)" fillOpacity={0.05} />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
              stroke="var(--muted-foreground)"
              opacity={0.5}
            />
            <YAxis
              domain={[0, yMax]}
              tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
              stroke="var(--muted-foreground)"
              opacity={0.5}
              label={{ value: "mg/L", angle: -90, position: "insideLeft", fontSize: 10, fill: "var(--muted-foreground)" }}
            />
            <ReferenceLine y={10} stroke="oklch(0.72 0.19 142)" strokeDasharray="4 4" opacity={0.6} />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                fontSize: "12px",
                fontFamily: "JetBrains Mono",
              }}
            />
            <Line
              type="monotone"
              dataKey="crp"
              stroke="var(--clinical-cyan)"
              strokeWidth={2}
              dot={{ r: 4, fill: "var(--clinical-cyan)", stroke: "var(--background)", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
