// 监控告警：我的通知、全部告警、通知设置。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
import { Ctx, ZONE, pct, num, signed, time, any, useLoad, Failed, ZoneBadge, Check, short, tone, Kpi } from "../components/common";
import { Diagnostic, GapList, FinancialSummary, ResearchResult, ReferenceQuality, ReferenceValuation, CompareRuns, Dialog, dimensionName, criterionName, human, when } from "../components/ui";
export function AlertCard({ a, children }: any) {
  return (
    <article className={`alert alert-${a.kind}`}>
      <h4><ZoneBadge zone={a.zone} /> {a.title}</h4>
      <p className="muted">{time(a.created_at)} · {{ news_hit: "资讯击球", zone_enter: "进入击球区", zone_exit: "离开击球区", hard_risk: "硬风险" }[a.kind as string] || a.kind}</p>
      <div className="body-text">{a.body}</div>
      {children}
    </article>
  );
}
export function Inbox({ busy, execute }: Ctx) {
  const box = useLoad<any>("/api/notifications");
  const act = async (fn: () => Promise<any>) => (await execute(fn, undefined, false)) !== undefined && box.reload();
  return (
    <>
      <Failed error={box.error} />
      {box.value && (
        <>
          <p>未读 {box.value.unread} 条。 {box.value.unread > 0 && <button className="quiet" disabled={busy} onClick={() => act(() => post("/api/notifications/read-all", {}))}>全部标为已读</button>}</p>
          {!box.value.items.length && <p>暂无告警。只有落进击球区的球才会提醒你。</p>}
          {box.value.items.map((n: any) => (
            <AlertCard key={n.id} a={n.alert}>
              {n.status === "unread" ? <button className="quiet" disabled={busy} onClick={() => act(() => post(`/api/notifications/${n.id}/read`, {}))}>标为已读</button> : <p className="muted">已读 {time(n.read_at)}</p>}
            </AlertCard>
          ))}
        </>
      )}
    </>
  );
}
export function AlertsList({ allow, busy, execute }: Ctx) {
  const list = useLoad<any[]>("/api/alerts");
  return (
    <>
      <p className="intro">告警只来自两类球：击球区变化（进入/离开甜区、硬风险否决），以及已确认的资讯击中甜区公司（或边角球公司遇重大利空）。</p>
      {any(allow, "source.manage", "strategy.publish", "system.configure") && (
        <button className="quiet" disabled={busy} onClick={async () => (await execute(() => post("/api/alerts/scan", {}), (r: any) => `扫描完成：新告警 ${r.zones.alerts + r.news.alerts} 条，邮件发出 ${r.email.sent} 封。`, false)) !== undefined && list.reload()}>
          立即扫描
        </button>
      )}
      <Failed error={list.error} />
      {list.value && !list.value.length && <p>暂无告警。</p>}
      {list.value?.map((a) => (
        <AlertCard key={a.id} a={a}>
          <p className="muted">邮件：{Object.entries(a.deliveries).map(([k, v]) => `${{ sent: "已发送", pending: "待发送", failed: "失败", skipped: "未配置跳过" }[k] || k} ${v}`).join("，") || "无收件邮箱"}</p>
        </AlertCard>
      ))}
    </>
  );
}
export function NotifySettings({ busy, execute }: Ctx) {
  const s = useLoad<any>("/api/notifications/settings");
  const [form, setForm] = useState<any>(null);
  useEffect(() => { if (s.value) setForm(s.value); }, [s.value]);
  if (!form) return <Failed error={s.error} />;
  return (
    <form className="form" onSubmit={(e) => { e.preventDefault(); execute(() => api("/api/notifications/settings", { method: "PUT", body: JSON.stringify({ ...form, email: form.email || null }) }), "通知设置已保存。", false); }}>
      <label>收件邮箱<input type="email" value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="name@example.com" /></label>
      <label className="inline"><input type="checkbox" checked={form.email_enabled} onChange={(e) => setForm({ ...form, email_enabled: e.target.checked })} /> 邮件提醒</label>
      <label className="inline"><input type="checkbox" checked={form.inapp_enabled} onChange={(e) => setForm({ ...form, inapp_enabled: e.target.checked })} /> 站内提醒</label>
      <button disabled={busy}>保存</button>
      <p className="muted">告警邮件由 admin@bytewatcher.xyz 发出。研究员、策略经理、系统管理员会收到告警。</p>
    </form>
  );
}

// ------------------------------------------------------------------ 后台设置
export function useUnread(deps: any[]) {
  const [n, setN] = useState<number | null>(null);
  useEffect(() => {
    api("/api/notifications").then((v) => setN(v.unread)).catch(() => setN(null));
  }, deps);
  return n;
}
