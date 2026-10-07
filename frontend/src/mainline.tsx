// 四层主线界面：资讯雷达 / 公司档案补充 / 击球区 / 监控告警 / 后台设置。
// Each view loads its own data; legacy research views stay in app.tsx.
import React, { useEffect, useState } from "react";
import { api, post, session, ApiError } from "./client";

type Ctx = { allow: (p: string) => boolean; busy: boolean; execute: any };

const ZONE: Record<string, string> = { sweet: "甜区", edge: "边角球", outside: "区外" };
const pct = (v: any) => (v == null ? "—" : `${Math.round(Number(v) * 100)}%`);
const num = (v: any, d = 2) => (v == null ? "—" : Number(v).toFixed(d));
const signed = (v: any) => (v == null ? "—" : (v > 0 ? "+" : "") + Number(v).toFixed(2));
const time = (v: any) => (v ? new Date(v).toLocaleString("zh-CN", { hour12: false }) : "时间未知");
const any = (allow: Ctx["allow"], ...ps: string[]) => ps.some(allow);

function useLoad<T>(path: string, deps: any[] = []) {
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

function Failed({ error }: { error: string }) {
  return error ? <p className="notice danger" role="alert">{error}</p> : null;
}

export function ZoneBadge({ zone }: { zone: string }) {
  return <span className={`zone zone-${zone}`}>{ZONE[zone] || zone}</span>;
}

function Check({ c }: any) {
  const mark = c.passed === true ? "✓" : c.passed === false ? "✗" : "？";
  return (
    <span className={`check check-${c.passed === true ? "ok" : c.passed === false ? "no" : "unknown"}`} title={c.detail}>
      {mark} {c.label}
    </span>
  );
}

// ------------------------------------------------------------------ 资讯雷达

export function NewsRadar({ allow, busy, execute }: Ctx) {
  const [filter, setFilter] = useState("");
  const events = useLoad<any[]>(`/api/news/events?limit=80${filter ? `&status=${filter}` : ""}`);
  const companies = useLoad<any[]>("/api/companies");
  const [open, setOpen] = useState<any>(null);
  const canReview = any(allow, "analysis.override", "quality.correct");
  const canScore = any(allow, "source.manage", "analysis.override");
  async function act(fn: () => Promise<any>, msg: string) {
    const r = await execute(fn, msg, false);
    if (r !== undefined) events.reload();
  }
  return (
    <>
      <p className="intro">每条资讯先合并成事件，再判断关联哪些公司、关联多紧（关联度 0–1）、影响多大（影响分 −1 到 1）。AI 先预判，研究员确认后才进入告警。</p>
      <div className="filters">
        <button className={filter ? "quiet" : ""} onClick={() => setFilter("")}>全部事件</button>
        <button className={filter === "needs_review" ? "" : "quiet"} onClick={() => setFilter("needs_review")}>待确认</button>
        {canScore && (
          <button className="quiet" disabled={busy} onClick={() => act(() => post("/api/news/score", {}), "已对待处理事件重新打分。")}>
            AI 打分待处理事件
          </button>
        )}
      </div>
      <Failed error={events.error} />
      {events.value && !events.value.length && <p>暂无资讯事件。在 后台设置 › 资讯源与导入 上传每日 Excel，或登记 RSS 源。</p>}
      {events.value?.map((e) => (
        <article key={e.id} className="event">
          <div className="event-head">
            <h3>{e.title}</h3>
            {e.impact_score != null && <span className={`impact ${e.impact_score >= 0 ? "up" : "down"}`}>影响 {signed(e.impact_score)}</span>}
          </div>
          <p className="muted">
            {time(e.last_published_at)} · {e.item_count} 条来源{e.category ? ` · ${e.category}` : ""} ·{" "}
            {e.ai_status === "scored" ? `AI 预判（${e.ai_model}）` : e.ai_status === "rule_only" ? `规则匹配${e.ai_error ? `（${e.ai_error}）` : ""}` : "待打分"}
          </p>
          <p>{e.summary.slice(0, 220)}{e.summary.length > 220 ? "…" : ""}</p>
          {e.links.length ? (
            <table>
              <thead><tr><th>关联公司</th><th>关联度</th><th>影响分</th><th>理由</th><th>状态</th>{canReview && <th>操作</th>}</tr></thead>
              <tbody>
                {e.links.map((l: any) => (
                  <LinkRow key={l.id} l={l} canReview={canReview} busy={busy} companies={companies.value || []}
                    review={(body: any, msg: string) => act(() => post(`/api/news/links/${l.id}/review`, body), msg)} />
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">暂未识别到关联公司。</p>
          )}
          <button className="text-button" onClick={async () => setOpen(open?.id === e.id ? null : await api(`/api/news/events/${e.id}`))}>
            {open?.id === e.id ? "收起来源" : "查看来源"}
          </button>
          {open?.id === e.id && (
            <ul className="sources">
              {open.items.map((i: any) => (
                <li key={i.id}>
                  <strong>{i.feed}</strong>：{i.title} <span className="muted">{time(i.published_at)}{i.source_text ? ` · ${i.source_text}` : ""}</span>
                  {i.url && <a href={i.url} target="_blank" rel="noreferrer"> 原文</a>}
                  {i.note && <div className="muted">备注：{i.note}</div>}
                </li>
              ))}
            </ul>
          )}
        </article>
      ))}
    </>
  );
}

function LinkRow({ l, canReview, busy, review, companies }: any) {
  const [impact, setImpact] = useState(l.impact ?? 0);
  const [relevance, setRelevance] = useState(l.relevance ?? 0.6);
  const [company, setCompany] = useState(l.company_id || "");
  const status = { proposed: "待确认", confirmed: "已确认", rejected: "已驳回" }[l.status as string] || l.status;
  return (
    <tr className={`link-${l.status}`}>
      <td>
        {l.company}
        {l.ticker_hint && <span className="muted"> {l.ticker_hint}</span>}
        {!l.company_id && canReview && l.status === "proposed" && (
          <select value={company} onChange={(e) => setCompany(e.target.value)} aria-label="对应公司档案">
            <option value="">对应到公司档案…</option>
            {companies.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
      </td>
      <td>{canReview && l.status === "proposed" ? <input type="number" min={0} max={1} step={0.05} value={relevance} onChange={(e) => setRelevance(Number(e.target.value))} aria-label="关联度" /> : num(l.relevance)}</td>
      <td>{canReview && l.status === "proposed" ? <input type="number" min={-1} max={1} step={0.1} value={impact} onChange={(e) => setImpact(Number(e.target.value))} aria-label="影响分" /> : signed(l.impact)}</td>
      <td className="rationale">{l.rationale}<div className="muted">{l.proposed_by.startsWith("ai:") ? "AI" : "规则"}</div></td>
      <td>{status}</td>
      {canReview && (
        <td>
          {l.status !== "confirmed" && (
            <button disabled={busy} onClick={() => review({ action: "confirm", impact, relevance, company_id: company || null }, "已确认关联；落进击球区会立即告警。")}>确认</button>
          )}
          {l.status !== "rejected" && (
            <button className="quiet" disabled={busy} onClick={() => review({ action: "reject" }, "已驳回该关联。")}>驳回</button>
          )}
        </td>
      )}
    </tr>
  );
}

// ------------------------------------------------------------------ 击球区

export function StrikeZone(_: Ctx) {
  const board = useLoad<any>("/api/strike-zone");
  const b = board.value;
  const m = b?.policy?.margin_of_safety;
  return (
    <>
      <p className="intro">只在三件事同时满足时挥棒：看得懂（能力圈）、是好生意、价格够便宜（安全边际）。A 股和 H 股分别判断，硬风险一票否决。</p>
      <Failed error={board.error} />
      {b && (
        <>
          <div className="zone-counts">
            {Object.entries(ZONE).map(([k, label]) => (
              <article key={k} className={`zone-card zone-${k}`}><h3>{b.counts[k] ?? 0}</h3><p>{label}</p></article>
            ))}
          </div>
          <p className="muted">
            安全边际 = 1 − 市盈率 ÷ 合理市盈率 {m?.fair_pe_ttm}；甜区要求 ≥ {pct(m?.sweet_minimum)}，{pct(m?.edge_minimum)}–{pct(m?.sweet_minimum)} 为边角球。能力圈要求评分覆盖度 ≥ {b.policy.circle_of_competence.minimum_coverage}。数字在后台配置，可调整。
          </p>
          <table>
            <thead><tr><th>公司</th><th>证券</th><th>区域</th><th>安全边际</th><th>三项检查</th><th>经营分</th><th>市盈率</th></tr></thead>
            <tbody>
              {b.rows.map((r: any) => (
                <tr key={r.security_id}>
                  <td>{r.company}</td>
                  <td>{r.ticker} <span className="muted">{r.market === "HK" ? "H股" : "A股"}</span></td>
                  <td><ZoneBadge zone={r.zone} /></td>
                  <td>{pct(r.margin_of_safety)}</td>
                  <td className="checks">{r.checks.map((c: any) => <Check key={c.key} c={c} />)}</td>
                  <td>{num(r.quality_score, 1)}</td>
                  <td>{num(r.pe_ttm, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">鼠标停在检查项上可看具体原因。更新于 {time(b.as_of)}。</p>
        </>
      )}
    </>
  );
}

// ------------------------------------------------------------------ 公司档案补充

export function CompanyMainline({ companyId }: { companyId: string }) {
  const zone = useLoad<any[]>(`/api/strike-zone/companies/${companyId}`, [companyId]);
  const news = useLoad<any[]>(`/api/news/events?company_id=${companyId}&limit=10`, [companyId]);
  return (
    <section className="company-mainline">
      <h3>击球区与关联资讯</h3>
      {zone.value?.map((r) => (
        <p key={r.security_id}>
          {r.ticker}（{r.market === "HK" ? "H股" : "A股"}）：<ZoneBadge zone={r.zone} /> 安全边际 {pct(r.margin_of_safety)}{" "}
          {r.checks.map((c: any) => <Check key={c.key} c={c} />)}
        </p>
      ))}
      {zone.error && <p className="muted">击球区：{zone.error}</p>}
      {news.value?.length ? (
        <ul className="sources">
          {news.value.map((e) => {
            const link = e.links.find((l: any) => l.company_id === companyId);
            return (
              <li key={e.id}>
                {e.title} <span className="muted">{time(e.last_published_at)}</span>
                {link && <span className={`impact ${link.impact >= 0 ? "up" : "down"}`}> 关联 {num(link.relevance)} · 影响 {signed(link.impact)} · {link.status === "confirmed" ? "已确认" : "待确认"}</span>}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="muted">暂无关联资讯。</p>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ 监控告警

function AlertCard({ a, children }: any) {
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

export function Sources(_: Ctx) {
  const list = useLoad<any[]>("/api/admin/sources");
  const layer: Record<string, string> = { news: "资讯", companies: "公司", strategy: "策略" };
  return (
    <>
      <Failed error={list.error} />
      <table>
        <thead><tr><th>数据源</th><th>喂给</th><th>内容</th><th>触发</th><th>市场</th><th>需要密钥</th></tr></thead>
        <tbody>
          {list.value?.map((s) => (
            <tr key={s.key}><td>{s.name}<div className="muted">{s.key}</div></td><td>{layer[s.layer] || s.layer}</td><td>{s.kind}</td>
              <td>{{ manual_script: "手动脚本", scheduled: "定时任务", upload: "上传" }[s.trigger as string] || s.trigger}</td>
              <td>{s.markets.join("、") || "—"}</td><td>{s.secret_env || "—"}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

async function upload(files: FileList) {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  form.append("score", "true");
  const r = await fetch("/api/news/import", { method: "POST", body: form, headers: { "X-Vip-Login": session.login, "X-Vip-Workspace": session.workspace } });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, typeof data.detail === "string" ? data.detail : "上传未完成");
  return data;
}

export function Feeds({ allow, busy, execute }: Ctx) {
  const feeds = useLoad<any[]>("/api/news/feeds");
  const [files, setFiles] = useState<FileList | null>(null);
  const [rss, setRss] = useState({ feed_key: "", name: "", url: "", schedule: "daily 08:30" });
  const canWrite = any(allow, "source.manage", "analysis.override");
  const canAdmin = any(allow, "source.manage", "system.configure");
  return (
    <>
      {canWrite && (
        <section>
          <h3>上传每日资讯 Excel</h3>
          <p className="muted">可一次选多个文件；按文件名识别资讯源（如“创新药每日动态_2026-09-30.xlsx”）。重复内容自动跳过，同一件事合并为一个事件。</p>
          <input type="file" accept=".xlsx" multiple onChange={(e) => setFiles(e.target.files)} />
          <button disabled={busy || !files?.length} onClick={async () => (await execute(() => upload(files!), (r: any) => `导入完成：新增 ${r.files.reduce((s: number, f: any) => s + f.new_items, 0)} 条，重复 ${r.files.reduce((s: number, f: any) => s + f.duplicate_items, 0)} 条；${r.scoring ? `打分 ${r.scoring.events} 个事件` : ""}${r.scoring?.error ? `（${r.scoring.error}，已用规则匹配）` : ""}。`, false)) !== undefined && feeds.reload()}>
            导入并打分
          </button>
        </section>
      )}
      <h3>资讯源</h3>
      <Failed error={feeds.error} />
      <table>
        <thead><tr><th>名称</th><th>类型</th><th>最近一次</th><th>状态</th>{canWrite && <th></th>}</tr></thead>
        <tbody>
          {feeds.value?.map((f) => (
            <tr key={f.id}><td>{f.name}{f.url && <div className="muted">{f.url}</div>}</td><td>{f.kind === "rss" ? `RSS${f.schedule ? ` · ${f.schedule}` : ""}` : "Excel 上传"}</td>
              <td>{time(f.last_run_at)}</td><td>{f.last_status || "—"}</td>
              {canWrite && <td>{f.kind === "rss" && <button className="quiet" disabled={busy} onClick={async () => (await execute(() => post(`/api/news/feeds/${f.id}/run`, {}), (r: any) => `抓取完成：新增 ${r.new_items} 条。`, false)) !== undefined && feeds.reload()}>立即抓取</button>}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      {canAdmin && (
        <form className="form" onSubmit={async (e) => { e.preventDefault(); (await execute(() => post("/api/admin/news-feeds", { ...rss, kind: "rss" }), "已登记 RSS 源。", false)) !== undefined && feeds.reload(); }}>
          <h4>登记 RSS / Atom 源</h4>
          <label>标识<input required value={rss.feed_key} onChange={(e) => setRss({ ...rss, feed_key: e.target.value })} placeholder="cls-telegraph" /></label>
          <label>名称<input required value={rss.name} onChange={(e) => setRss({ ...rss, name: e.target.value })} /></label>
          <label>地址<input required type="url" value={rss.url} onChange={(e) => setRss({ ...rss, url: e.target.value })} /></label>
          <label>计划<input value={rss.schedule} onChange={(e) => setRss({ ...rss, schedule: e.target.value })} /></label>
          <button disabled={busy}>登记</button>
          <p className="muted">定时抓取由服务器 cron 执行 python -m app.jobs news。</p>
        </form>
      )}
    </>
  );
}

const PRESETS = [
  { provider_key: "deepseek", name: "DeepSeek", base_url: "https://api.deepseek.com", model: "deepseek-chat", api_key_env: "VIP_DEEPSEEK_API_KEY" },
  { provider_key: "qwen", name: "通义千问", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", api_key_env: "VIP_QWEN_API_KEY" },
  { provider_key: "moonshot", name: "Kimi", base_url: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k", api_key_env: "VIP_MOONSHOT_API_KEY" },
  { provider_key: "zhipu", name: "智谱 GLM", base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-plus", api_key_env: "VIP_ZHIPU_API_KEY" },
  { provider_key: "openai", name: "OpenAI", base_url: "https://api.openai.com/v1", model: "gpt-4o-mini", api_key_env: "VIP_OPENAI_API_KEY" },
];

export function Models({ busy, execute }: Ctx) {
  const list = useLoad<any>("/api/admin/llm-providers");
  const blank = { ...PRESETS[0], is_default: true, enabled: true, temperature: 0 };
  const [form, setForm] = useState<any>(blank);
  const [editing, setEditing] = useState<string | null>(null);
  const v = list.value;
  async function save(e: any) {
    e.preventDefault();
    const r = await execute(() => (editing ? api(`/api/admin/llm-providers/${editing}`, { method: "PUT", body: JSON.stringify(form) }) : post("/api/admin/llm-providers", form)), "模型配置已保存。", false);
    if (r !== undefined) { setEditing(null); setForm(blank); list.reload(); }
  }
  return (
    <>
      <p className="intro">资讯关联打分使用 OpenAI 兼容接口的大模型，默认 DeepSeek。这里只登记“密钥放在哪个环境变量”，密钥本身由服务器环境注入，不进数据库。</p>
      <Failed error={list.error} />
      {v && (
        <>
          <p>当前使用：<strong>{v.active || `${v.builtin_default.name}（内置默认）`}</strong>{!v.providers.length && !v.builtin_default.key_configured && <span className="notice"> 服务器尚未设置 {v.builtin_default.api_key_env}，资讯关联暂用规则匹配。</span>}</p>
          <table>
            <thead><tr><th>模型</th><th>地址</th><th>密钥变量</th><th>状态</th><th></th></tr></thead>
            <tbody>
              {v.providers.map((p: any) => (
                <tr key={p.id}><td>{p.name}<div className="muted">{p.model}</div></td><td>{p.base_url}</td><td>{p.api_key_env} {p.key_configured ? "✓ 已设置" : "✗ 未设置"}</td>
                  <td>{p.enabled ? (p.is_default ? "默认" : "可用") : "停用"}</td>
                  <td><button className="quiet" onClick={() => { setEditing(p.id); setForm({ ...p, temperature: p.options?.temperature ?? 0 }); }}>编辑</button></td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <form className="form" onSubmit={save}>
        <h4>{editing ? "编辑模型" : "添加模型"}</h4>
        {!editing && <label>预设<select onChange={(e) => setForm({ ...form, ...PRESETS[Number(e.target.value)] })}>{PRESETS.map((p, i) => <option key={p.provider_key} value={i}>{p.name}</option>)}</select></label>}
        {["provider_key", "name", "base_url", "model", "api_key_env"].map((k) => (
          <label key={k}>{{ provider_key: "标识", name: "名称", base_url: "接口地址", model: "模型名", api_key_env: "密钥环境变量" }[k]}<input required value={form[k] || ""} disabled={k === "provider_key" && !!editing} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></label>
        ))}
        <label>温度<input type="number" min={0} max={2} step={0.1} value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} /></label>
        <label className="inline"><input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /> 设为默认</label>
        <label className="inline"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> 启用</label>
        <button disabled={busy}>保存</button>
        {editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setForm(blank); }}>取消</button>}
      </form>
    </>
  );
}

export function NotifyAdmin(_: Ctx) {
  const s = useLoad<any>("/api/admin/notify");
  const v = s.value;
  return (
    <>
      <Failed error={s.error} />
      {v && (
        <>
          <p>发件人：<strong>{v.sender_name} &lt;{v.sender}&gt;</strong></p>
          <p>SMTP：{v.smtp_configured ? `${v.smtp_host}:${v.smtp_port}${v.smtp_starttls ? "（STARTTLS）" : "（TLS）"}` : "未配置（只发站内通知；设置 VIP_SMTP_HOST 等环境变量后启用邮件）"}</p>
          <p>邮件投递：{Object.entries(v.email_counts).map(([k, n]) => `${k} ${n}`).join("，") || "暂无"}</p>
          <h4>收件人（角色：{v.recipient_roles.join("、")}）</h4>
          <table>
            <thead><tr><th>人员</th><th>邮箱</th><th>邮件</th></tr></thead>
            <tbody>{v.recipients.map((r: any) => <tr key={r.login}><td>{r.name}</td><td>{r.email || "未填写"}</td><td>{r.email_enabled ? "开" : "关"}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </>
  );
}

export function useUnread(deps: any[]) {
  const [n, setN] = useState<number | null>(null);
  useEffect(() => {
    api("/api/notifications").then((v) => setN(v.unread)).catch(() => setN(null));
  }, deps);
  return n;
}
