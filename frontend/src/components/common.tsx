// 页面共用的小组件与格式化工具。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
export type Ctx = { allow: (p: string) => boolean; busy: boolean; execute: any };
export const ZONE: Record<string, string> = { sweet: "甜区", edge: "边角球", outside: "区外" };
export const pct = (v: any) => (v == null ? "—" : `${Math.round(Number(v) * 100)}%`);
export const num = (v: any, d = 2) => (v == null ? "—" : Number(v).toFixed(d));
export const signed = (v: any) => (v == null ? "—" : (v > 0 ? "+" : "") + Number(v).toFixed(2));
export const time = (v: any) => (v ? new Date(v).toLocaleString("zh-CN", { hour12: false }) : "时间未知");
export const any = (allow: Ctx["allow"], ...ps: string[]) => ps.some(allow);
export function useLoad<T>(path: string, deps: any[] = []) {
  const [value, setValue] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setError("");
    api(path)
      .then((v) => live && setValue(v))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [path, tick, ...deps]);
  return { value, error, reload: () => setTick((t) => t + 1) };
}
export function Failed({ error }: { error: string }) {
  return error ? <p className="notice danger" role="alert">{error}</p> : null;
}
export function ZoneBadge({ zone }: { zone: string }) {
  return <span className={`zone zone-${zone}`}>{ZONE[zone] || zone}</span>;
}
export function Check({ c }: any) {
  const mark = c.passed === true ? "✓" : c.passed === false ? "✗" : "？";
  return (
    <span className={`check check-${c.passed === true ? "ok" : c.passed === false ? "no" : "unknown"}`} title={c.detail}>
      {mark} {c.label}
    </span>
  );
}

// ------------------------------------------------------------------ 资讯雷达
export const short = (v: any) => {
  if (!v) return "—";
  const d = new Date(v);
  const today = new Date();
  return d.toDateString() === today.toDateString()
    ? d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })
    : d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
};
export const tone = (v: any) => (v == null ? "" : v >= 0 ? "up" : "down");
export function Kpi({ label, value, hint }: any) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}
