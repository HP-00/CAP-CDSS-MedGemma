/** Clinical value formatters for dashboard display. */

import type { LabValue } from "@/types/pipeline";

export function formatLabValue(lab: LabValue): string {
  return `${lab.value} ${lab.unit}`;
}

export function isAbnormal(lab: LabValue): boolean {
  return lab.abnormal_flag === true || lab.abnormal === true;
}

export function formatAge(age: number, sex?: string): string {
  const parts = [`${age}yo`];
  if (sex) parts.push(sex);
  return parts.join(" ");
}

export function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

export function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  return `${seconds.toFixed(1)}s`;
}

export function formatPercentChange(pct: number): string {
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(0)}%`;
}

export function formatPatientName(name: string): string {
  return name.toUpperCase();
}

export function formatAdmissionDate(date: string): string {
  // Already pre-formatted in patient-data; pass through
  return date;
}
