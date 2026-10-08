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

const short = (v: any) => {
  if (!v) return "—";
  const d = new Date(v);
  const today = new Date();
  return d.toDateString() === today.toDateString()
    ? d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })
    : d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
};
const tone = (v: any) => (v == null ? "" : v >= 0 ? "up" : "down");

function Kpi({ label, value, hint }: any) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function NewsRadar({ allow, busy, execute }: Ctx) {
  const [filter, setFilter] = useState("");
  const events = useLoad<any[]>(`/api/news/events?limit=80${filter ? `&status=${filter}` : ""}`);
  const companies = useLoad<any[]>("/api/companies");
  const [selId, setSelId] = useState<string>("");
  const [detail, setDetail] = useState<any>(null);
  const canReview = any(allow, "analysis.override", "quality.correct");
  const canScore = any(allow, "source.manage", "analysis.override");
  const list = events.value || [];
  const sel = list.find((e) => e.id === selId) || list[0];
  useEffect(() => {
    let live = true;
    setDetail(null);
    if (sel) api(`/api/news/events/${sel.id}`).then((d) => live && setDetail(d)).catch(() => {});
    return () => {
      live = false;
    };
  }, [sel?.id]);
  async function act(fn: () => Promise<any>, msg: string) {
    const r = await execute(fn, msg, false);
    if (r !== undefined) events.reload();
  }
  const links = list.flatMap((e) => e.links);
  const pending = links.filter((l: any) => l.status === "proposed").length;
  const ups = list.filter((e) => e.impact_score != null && e.impact_score >= 0.3).length;
  const downs = list.filter((e) => e.impact_score != null && e.impact_score <= -0.3).length;
  const items = list.reduce((n, e) => n + (e.item_count || 0), 0);
  return (
    <>
      <p className="intro">每条资讯先合并成事件，再判断关联哪些公司、关联多紧（关联度 0–1）、影响多大（影响分 −1 到 1）。AI 先预判，研究员确认后才进入告警。</p>
      <div className="kpis">
        <Kpi label="事件" value={list.length} hint={`${items} 条资讯合并而来`} />
        <Kpi label="待确认关联" value={pending} hint="AI 已预判，等你拍板" />
        <Kpi label="利好 / 利空" value={<><span className="up">{ups}</span> <span className="muted">/</span> <span className="down">{downs}</span></>} hint="影响分绝对值 ≥ 0.3" />
        <Kpi label="已确认关联" value={links.filter((l: any) => l.status === "confirmed").length} hint="已确认的才会触发告警" />
      </div>
      <Failed error={events.error} />
      <div className="radar">
        <div className="panel">
          <div className="panel-head">
            <h3>事件流</h3>
            <div className="seg" role="group" aria-label="筛选事件">
              <button aria-pressed={!filter} onClick={() => setFilter("")}>全部事件</button>
              <button aria-pressed={filter === "needs_review"} onClick={() => setFilter("needs_review")}>待确认</button>
            </div>
            <div className="right">
              {canScore && (
                <button className="quiet small" disabled={busy} onClick={() => act(() => post("/api/news/score", {}), "已对待处理事件重新打分。")}>
                  AI 打分待处理事件
                </button>
              )}
            </div>
          </div>
          {events.value && !list.length ? (
            <p className="empty">暂无资讯事件。在 后台设置 › 资讯源与导入 上传每日 Excel，或登记 RSS 源。</p>
          ) : (
            <div className="table-scroll">
              <table className="event-table">
                <thead>
                  <tr><th>时间</th><th>事件</th><th>关联公司</th><th>关联度</th><th>影响分</th><th>状态</th></tr>
                </thead>
                <tbody>
                  {list.map((e) => {
                    const top = Math.max(0, ...e.links.map((l: any) => Number(l.relevance) || 0));
                    const waiting = e.links.some((l: any) => l.status === "proposed");
                    return (
                      <tr key={e.id} aria-selected={sel?.id === e.id} onClick={() => setSelId(e.id)}>
                        <td className="num muted">{short(e.last_published_at)}</td>
                        <td>
                          <div className="event-title">{e.title}</div>
                          <div className="event-meta">
                            {e.category ? `${e.category} · ` : ""}{e.item_count} 条来源 ·{" "}
                            {e.ai_status === "scored" ? "AI 预判" : e.ai_status === "rule_only" ? "规则匹配" : "待打分"}
                          </div>
                        </td>
                        <td>
                          {e.links.slice(0, 2).map((l: any) => (
                            <span key={l.id} className="chip">{l.company}{l.ticker_hint && <span className="muted num"> {l.ticker_hint}</span>}</span>
                          ))}
                          {e.links.length > 2 && <span className="muted">+{e.links.length - 2}</span>}
                          {!e.links.length && <span className="muted">—</span>}
                        </td>
                        <td className="num" style={{ whiteSpace: "nowrap" }}>
                          {e.links.length ? <>{num(top)}<span className="bar"><i style={{ width: `${Math.round(top * 100)}%` }} /></span></> : "—"}
                        </td>
                        <td className={`num ${tone(e.impact_score)}`} style={{ fontWeight: 600 }}>{signed(e.impact_score)}</td>
                        <td>{waiting ? <span className="pill pill-wait">待确认</span> : <span className="pill pill-ok">{e.links.length ? "已处理" : "无关联"}</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {sel && (
          <aside className="panel detail" aria-label="事件详情">
            <div className="panel-head">
              <h3>事件详情</h3>
              <span className="right">{pending ? `${pending} 个关联待确认` : "全部已处理"}</span>
            </div>
            <div className="panel-sec">
              <div className="detail-title">{sel.title}</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {time(sel.last_published_at)}{sel.category ? ` · ${sel.category}` : ""} ·{" "}
                {sel.ai_status === "scored" ? `AI 预判（${sel.ai_model}）` : sel.ai_status === "rule_only" ? `规则匹配${sel.ai_error ? `（${sel.ai_error}）` : ""}` : "待打分"}
              </div>
              {sel.summary && <p style={{ marginTop: 10 }}>{sel.summary.slice(0, 400)}{sel.summary.length > 400 ? "…" : ""}</p>}
            </div>
            <div className="panel-sec">
              <div className="sec-label">关联公司</div>
              {sel.links.length ? (
                sel.links.map((l: any) => (
                  <LinkCard key={l.id} l={l} canReview={canReview} busy={busy} companies={companies.value || []}
                    review={(body: any, msg: string) => act(() => post(`/api/news/links/${l.id}/review`, body), msg)} />
                ))
              ) : (
                <p className="muted">暂未识别到关联公司。</p>
              )}
            </div>
            <div className="panel-sec">
              <div className="sec-label">合并的 {sel.item_count} 条来源</div>
              {!detail ? (
                <p className="muted">读取来源…</p>
              ) : (
                <ul className="sources">
                  {detail.items.map((i: any) => (
                    <li key={i.id}>
                      <div><strong>{i.feed}</strong>：{i.title}</div>
                      <div className="muted">
                        {time(i.published_at)}{i.source_text ? ` · ${i.source_text}` : ""}
                        {i.url && <> · <a href={i.url} target="_blank" rel="noreferrer">原文</a></>}
                      </div>
                      {i.note && <div className="muted">备注：{i.note}</div>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        )}
      </div>
    </>
  );
}

function LinkCard({ l, canReview, busy, review, companies }: any) {
  const [impact, setImpact] = useState(l.impact ?? 0);
  const [relevance, setRelevance] = useState(l.relevance ?? 0.6);
  const [company, setCompany] = useState(l.company_id || "");
  const editing = canReview && l.status === "proposed";
  const status = { proposed: "待确认", confirmed: "已确认", rejected: "已驳回" }[l.status as string] || l.status;
  return (
    <div className={`link-card link-${l.status}`}>
      <div className="head">
        <strong>{l.company}</strong>
        {l.ticker_hint && <span className="muted num">{l.ticker_hint}</span>}
        <span style={{ marginLeft: "auto" }} className={`pill ${l.status === "proposed" ? "pill-wait" : "pill-ok"}`}>{status}</span>
      </div>
      {!l.company_id && editing && (
        <select value={company} onChange={(e) => setCompany(e.target.value)} aria-label="对应公司档案">
          <option value="">对应到公司档案…</option>
          {companies.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      )}
      <div className="scores">
        <div>
          <div className="muted">关联度</div>
          {editing ? (
            <input type="number" min={0} max={1} step={0.05} value={relevance} onChange={(e) => setRelevance(Number(e.target.value))} aria-label="关联度" />
          ) : (
            <div className="big">{num(l.relevance)}</div>
          )}
        </div>
        <div>
          <div className="muted">影响分</div>
          {editing ? (
            <input type="number" min={-1} max={1} step={0.1} value={impact} onChange={(e) => setImpact(Number(e.target.value))} aria-label="影响分" />
          ) : (
            <div className={`big ${tone(l.impact)}`}>{signed(l.impact)}</div>
          )}
        </div>
      </div>
      {l.rationale && <div className="why">{l.rationale}（{l.proposed_by.startsWith("ai:") ? "AI" : "规则"}）</div>}
      {canReview && (
        <div style={{ marginTop: 8 }}>
          {l.status !== "confirmed" && (
            <button disabled={busy} onClick={() => review({ action: "confirm", impact, relevance, company_id: company || null }, "已确认关联；落进击球区会立即告警。")}>确认关联</button>
          )}
          {l.status !== "rejected" && (
            <button className="quiet" disabled={busy} onClick={() => review({ action: "reject" }, "已驳回该关联。")}>驳回</button>
          )}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 击球区

function ZoneScatter({ rows, sweet, edge }: { rows: any[]; sweet: number; edge: number }) {
  const pts = rows.filter((r) => r.margin_of_safety != null && r.quality_score != null);
  const W = 560, H = 380, l = 44, b = 40, r = 18, t = 18;
  const ms = pts.map((p) => Number(p.margin_of_safety));
  const qs = pts.map((p) => Number(p.quality_score));
  const x0 = Math.min(-0.2, Math.floor(Math.min(0, ...ms) * 10) / 10);
  const x1 = Math.max(0.6, Math.ceil(Math.max(0, ...ms) * 10) / 10);
  const y0 = Math.min(50, Math.floor(Math.min(100, ...qs) / 10) * 10);
  const y1 = 100;
  const X = (v: number) => l + ((v - x0) / (x1 - x0)) * (W - l - r);
  const Y = (v: number) => H - b - ((v - y0) / (y1 - y0)) * (H - b - t);
  const xt: number[] = [];
  for (let v = Math.ceil(x0 * 5) / 5; v <= x1 + 1e-9; v += 0.2) xt.push(Math.round(v * 100) / 100);
  const yt: number[] = [];
  for (let v = y0; v <= y1; v += 10) yt.push(v);
  return (
    <svg className="scatter" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="击球区散点图：横轴安全边际，纵轴经营分">
      <rect className="edge" x={X(edge)} y={t} width={X(sweet) - X(edge)} height={H - b - t} />
      <rect className="sweet" x={X(sweet)} y={t} width={X(x1) - X(sweet)} height={H - b - t} />
      {xt.map((v) => (
        <g key={`x${v}`}>
          <line className="grid" x1={X(v)} x2={X(v)} y1={t} y2={H - b} />
          <text className="tick" x={X(v)} y={H - b + 16} textAnchor="middle">{Math.round(v * 100)}%</text>
        </g>
      ))}
      {yt.map((v) => (
        <g key={`y${v}`}>
          <line className="grid" x1={l} x2={W - r} y1={Y(v)} y2={Y(v)} />
          <text className="tick" x={l - 8} y={Y(v) + 4} textAnchor="end">{v}</text>
        </g>
      ))}
      <text className="zlabel" x={(X(sweet) + X(x1)) / 2} y={t + 18} textAnchor="middle">甜区 · 可以挥棒</text>
      <text className="zlabel soft" x={(X(edge) + X(sweet)) / 2} y={t + 18} textAnchor="middle">边角球</text>
      <text className="tick" x={(l + W - r) / 2} y={H - 4} textAnchor="middle">安全边际 →</text>
      <text className="tick" x={l + 6} y={t + 12}>↑ 经营分</text>
      {pts.map((p) => (
        <g key={p.security_id}>
          <circle className={`dot dot-${p.zone}`} cx={X(Number(p.margin_of_safety))} cy={Y(Number(p.quality_score))} r={6}>
            <title>{`${p.company} ${p.ticker}：安全边际 ${pct(p.margin_of_safety)}，经营分 ${num(p.quality_score, 1)}`}</title>
          </circle>
          <text className="name" x={X(Number(p.margin_of_safety)) + 10} y={Y(Number(p.quality_score)) + 4}>
            {p.company}{p.market === "HK" ? " H" : ""}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function StrikeZone(_: Ctx) {
  const board = useLoad<any>("/api/strike-zone");
  const [only, setOnly] = useState("");
  const b = board.value;
  const m = b?.policy?.margin_of_safety;
  const rows = (b?.rows || []).filter((r: any) => !only || r.zone === only);
  const plotted = (b?.rows || []).filter((r: any) => r.margin_of_safety != null && r.quality_score != null).length;
  return (
    <>
      <p className="intro">只在三件事同时满足时挥棒：看得懂（能力圈）、是好生意、价格够便宜（安全边际）。A 股和 H 股分别判断，硬风险一票否决。</p>
      <Failed error={board.error} />
      {b && (
        <>
          <div className="kpis">
            <Kpi label="甜区" value={<span style={{ color: "var(--accent)" }}>{b.counts.sweet ?? 0}</span>} hint={`安全边际 ≥ ${pct(m?.sweet_minimum)} 且三项都过`} />
            <Kpi label="边角球" value={b.counts.edge ?? 0} hint={`${pct(m?.edge_minimum)}–${pct(m?.sweet_minimum)} 或依据不全，只观察`} />
            <Kpi label="区外" value={b.counts.outside ?? 0} hint="只记录，不处理" />
            <Kpi label="证券总数" value={b.rows.length} hint="A 股、H 股分别计" />
          </div>
          <div className="zone-layout">
            <div className="panel">
              <div className="panel-head">
                <h3>击球区</h3>
                <span className="right">合理市盈率 {m?.fair_pe_ttm} · 甜区门槛 {pct(m?.sweet_minimum)}</span>
              </div>
              <div className="panel-body">
                <ZoneScatter rows={b.rows} sweet={Number(m?.sweet_minimum ?? 0.3)} edge={Number(m?.edge_minimum ?? 0.1)} />
                <p className="muted">
                  安全边际 = 1 − 市盈率 ÷ 合理市盈率；能力圈要求评分覆盖度 ≥ {b.policy.circle_of_competence.minimum_coverage}。
                  {plotted < b.rows.length && ` 另有 ${b.rows.length - plotted} 只证券缺安全边际或经营分，未画在图上。`}数字在后台配置，可调整。
                </p>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <h3>证券列表</h3>
                <div className="seg" role="group" aria-label="按区域筛选">
                  <button aria-pressed={!only} onClick={() => setOnly("")}>全部</button>
                  {Object.entries(ZONE).map(([k, label]) => (
                    <button key={k} aria-pressed={only === k} onClick={() => setOnly(k)}>{label}</button>
                  ))}
                </div>
              </div>
              <div className="table-scroll">
                <table>
                  <thead><tr><th>公司</th><th>区域</th><th>安全边际</th><th>市盈率</th><th>经营分</th><th>三项检查</th></tr></thead>
                  <tbody>
                    {rows.map((r: any) => (
                      <tr key={r.security_id}>
                        <td><strong>{r.company}</strong> <span className="muted num">{r.ticker} {r.market === "HK" ? "H股" : "A股"}</span></td>
                        <td><ZoneBadge zone={r.zone} /></td>
                        <td className="num" style={{ fontWeight: 600 }}>{pct(r.margin_of_safety)}</td>
                        <td className="num">{num(r.pe_ttm, 1)}</td>
                        <td className="num">{num(r.quality_score, 1)}</td>
                        <td className="checks">{r.checks.map((c: any) => <Check key={c.key} c={c} />)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!rows.length && <p className="empty">这个区域暂时没有证券。</p>}
              </div>
              <p className="muted" style={{ padding: "0 16px 12px" }}>鼠标停在检查项上可看具体原因。更新于 {time(b.as_of)}。</p>
            </div>
          </div>
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
  { provider_key: "deepseek", name: "DeepSeek", base_url: "https://api.deepseek.com", model: "deepseek-chat", api_key_env: "VIP_DEEPSEEK_API_KEY", search_mode: "none" },
  { provider_key: "qwen", name: "通义千问", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", api_key_env: "VIP_QWEN_API_KEY", search_mode: "qwen_enable_search" },
  { provider_key: "zhipu", name: "智谱 GLM", base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-air", api_key_env: "VIP_ZHIPU_API_KEY", search_mode: "zhipu_web_search" },
  { provider_key: "kimi", name: "Kimi", base_url: "https://api.moonshot.cn/v1", model: "kimi-k3", api_key_env: "VIP_MOONSHOT_API_KEY", search_mode: "kimi_search" },
  { provider_key: "openai", name: "OpenAI", base_url: "https://api.openai.com/v1", model: "gpt-4o-mini", api_key_env: "VIP_OPENAI_API_KEY", search_mode: "none" },
];
const SEARCH_LABEL: Record<string, string> = { none: "不联网", qwen_enable_search: "通义 · 内置联网", zhipu_web_search: "智谱 · web_search", kimi_search: "Kimi · 官方搜索" };

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
            <thead><tr><th>模型</th><th>地址</th><th>密钥变量</th><th>联网</th><th>状态</th><th></th></tr></thead>
            <tbody>
              {v.providers.map((p: any) => (
                <tr key={p.id}><td>{p.name}<div className="muted">{p.model}</div></td><td>{p.base_url}</td><td>{p.api_key_env} {p.key_configured ? "✓ 已设置" : "✗ 未设置"}</td>
                  <td>{SEARCH_LABEL[p.search_mode] || p.search_mode}</td>
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
        <label>联网方式<select value={form.search_mode || "none"} onChange={(e) => setForm({ ...form, search_mode: e.target.value })}>
          {Object.entries((v?.search_modes as Record<string, string>) || SEARCH_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select></label>
        <p className="muted">采集定时器只能选能联网的模型。联网用的是厂商自带的搜索，和对话共用同一个密钥，不需要另配搜索服务。</p>
        <label>温度<input type="number" min={0} max={2} step={0.1} value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} /></label>
        <label className="inline"><input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /> 设为默认</label>
        <label className="inline"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> 启用</label>
        <button disabled={busy}>保存</button>
        {editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setForm(blank); }}>取消</button>}
      </form>
    </>
  );
}

// ------------------------------------------------------------------ 采集定时器 / Skill

const WEEK = ["一", "二", "三", "四", "五", "六", "日"];
const RUN_STATUS: Record<string, string> = { running: "执行中", succeeded: "成功", failed: "失败" };

export function Collectors({ busy, execute }: Ctx) {
  const list = useLoad<any[]>("/api/admin/collectors");
  const opts = useLoad<any>("/api/admin/collectors/options");
  const blank = { name: "", prompt: "", provider_id: "", skill_id: "", enabled: true, kind: "daily", times: "08:30", weekdays: [1, 2, 3, 4, 5, 6, 7], minutes: 240 };
  const [form, setForm] = useState<any>(blank);
  const [editing, setEditing] = useState<string | null>(null);
  const [runsOf, setRunsOf] = useState<string | null>(null);
  const runs = useLoad<any[]>(runsOf ? `/api/admin/collectors/${runsOf}/runs` : "/api/admin/collectors", [runsOf]);
  const searchable = (opts.value?.providers || []).filter((p: any) => p.search_mode !== "none");
  const body = () => ({
    name: form.name, prompt: form.prompt, provider_id: form.provider_id || searchable[0]?.id, skill_id: form.skill_id || null, enabled: form.enabled,
    schedule: form.kind === "daily" ? { type: "daily", times: String(form.times).split(/[,，\s]+/).filter(Boolean), weekdays: form.weekdays } : { type: "interval", minutes: Number(form.minutes) },
  });
  async function save(e: any) {
    e.preventDefault();
    const r = await execute(() => (editing ? api(`/api/admin/collectors/${editing}`, { method: "PUT", body: JSON.stringify(body()) }) : post("/api/admin/collectors", body())), "采集定时器已保存。", false);
    if (r !== undefined) { setEditing(null); setForm(blank); list.reload(); }
  }
  function edit(t: any) {
    setEditing(t.id);
    setForm({ name: t.name, prompt: t.prompt, provider_id: t.provider_id || "", skill_id: t.skill_id || "", enabled: t.enabled, kind: t.schedule.type,
      times: (t.schedule.times || ["08:30"]).join(", "), weekdays: t.schedule.weekdays || [1, 2, 3, 4, 5, 6, 7], minutes: t.schedule.minutes || 240 });
  }
  return (
    <>
      <p className="intro">像 Agent 定时任务一样采集资讯：写好提示词、选一个能联网的模型（可再选一个 Skill 让模型按流程走），到点自动执行。采到的资讯进入资讯雷达，和 Excel、RSS 一样去重、关联公司、等你确认。时间按北京时间。</p>
      <Failed error={list.error || opts.error} />
      {opts.value && !searchable.length && <p className="notice">还没有能联网的模型。先到 模型配置 添加通义、智谱或 Kimi，并选择联网方式。</p>}
      <table>
        <thead><tr><th>定时器</th><th>模型 / Skill</th><th>周期</th><th>下次执行</th><th>最近一次</th><th></th></tr></thead>
        <tbody>
          {list.value?.map((t) => (
            <tr key={t.id}>
              <td>{t.name}<div className="muted">{t.prompt.slice(0, 60)}{t.prompt.length > 60 ? "…" : ""}</div></td>
              <td>{t.provider || "—"}<div className="muted">{t.skill ? `Skill：${t.skill}` : "不用 Skill"}</div></td>
              <td>{t.enabled ? t.schedule_text : "已停用"}</td>
              <td>{t.enabled ? time(t.next_run_at) : "—"}</td>
              <td>{t.last_status || "尚未执行"}<div className="muted">{t.last_run_at ? time(t.last_run_at) : ""}</div></td>
              <td className="actions">
                <button className="quiet" disabled={busy} onClick={async () => { const r = await execute(() => post(`/api/admin/collectors/${t.id}/run`, {}), (x: any) => (x.status === "succeeded" ? `采集完成：采到 ${x.items_found} 条，新增 ${x.stats.new_items} 条。` : `采集失败：${x.error}`), false); if (r !== undefined) { list.reload(); runs.reload(); } }}>立即执行</button>
                <button className="quiet" onClick={() => edit(t)}>编辑</button>
                <button className="quiet" onClick={() => setRunsOf(runsOf === t.id ? null : t.id)}>{runsOf === t.id ? "收起记录" : "执行记录"}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {runsOf && (
        <section>
          <h4>执行记录</h4>
          <table>
            <thead><tr><th>开始</th><th>触发</th><th>结果</th><th>模型 / Skill</th><th>说明</th></tr></thead>
            <tbody>
              {(runs.value || []).map((r: any) => (
                <tr key={r.id}><td>{time(r.started_at)}</td><td>{r.trigger === "manual" ? "手动" : "定时"}</td>
                  <td>{RUN_STATUS[r.status] || r.status}{r.status === "succeeded" && ` · ${r.items_found} 条`}</td>
                  <td>{r.model || "—"}<div className="muted">{r.skill_key ? `${r.skill_key} v${r.skill_version}` : ""}</div></td>
                  <td>{r.error || (r.stats?.searches?.length ? `搜索：${r.stats.searches.join("；")}` : r.stats?.new_items != null ? `新增 ${r.stats.new_items}，重复 ${r.stats.duplicate_items}` : "—")}
                    {r.output_excerpt && <details><summary>模型原始输出</summary><pre>{r.output_excerpt}</pre></details>}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <form className="form" onSubmit={save}>
        <h4>{editing ? "编辑采集定时器" : "新建采集定时器"}</h4>
        <label>名称<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="创新药重点公司早报" /></label>
        <label>提示词<textarea required value={form.prompt} onChange={(e) => setForm({ ...form, prompt: e.target.value })} placeholder="采集过去 24 小时内诺诚健华、百济神州、信达生物的公告、临床进展和重要新闻……" /></label>
        <label>模型<select required value={form.provider_id || searchable[0]?.id || ""} onChange={(e) => setForm({ ...form, provider_id: e.target.value })}>
          {searchable.map((p: any) => <option key={p.id} value={p.id}>{p.name} · {p.model}（{p.search_label}）{p.key_configured ? "" : " · 密钥未设置"}</option>)}
        </select></label>
        <label>Skill（可选）<select value={form.skill_id} onChange={(e) => setForm({ ...form, skill_id: e.target.value })}>
          <option value="">不用 Skill</option>
          {(opts.value?.skills || []).map((s: any) => <option key={s.id} value={s.id}>{s.name}{s.enabled ? "" : "（已停用）"}</option>)}
        </select></label>
        <label>周期<select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}><option value="daily">每天定时</option><option value="interval">固定间隔</option></select></label>
        {form.kind === "daily" ? (
          <>
            <label>执行时间（可多个，逗号分隔）<input value={form.times} onChange={(e) => setForm({ ...form, times: e.target.value })} placeholder="08:30, 17:00" /></label>
            <div className="chips">{WEEK.map((w, i) => (
              <label key={w} className="inline"><input type="checkbox" checked={form.weekdays.includes(i + 1)} onChange={(e) => setForm({ ...form, weekdays: e.target.checked ? [...form.weekdays, i + 1].sort() : form.weekdays.filter((d: number) => d !== i + 1) })} /> 周{w}</label>
            ))}</div>
          </>
        ) : (
          <label>间隔分钟（不少于 {opts.value?.min_interval_minutes ?? 60}）<input type="number" min={opts.value?.min_interval_minutes ?? 60} step={30} value={form.minutes} onChange={(e) => setForm({ ...form, minutes: e.target.value })} /></label>
        )}
        <label className="inline"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> 启用</label>
        <button disabled={busy || !searchable.length}>保存</button>
        {editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setForm(blank); }}>取消</button>}
        <p className="muted">定时执行需要服务器每 5 分钟跑一次 python -m app.jobs collect。</p>
      </form>
    </>
  );
}

export function Skills({ busy, execute }: Ctx) {
  const list = useLoad<any[]>("/api/admin/skills");
  const blank = { skill_key: "", name: "", description: "", body: "", enabled: true };
  const [form, setForm] = useState<any>(blank);
  const [editing, setEditing] = useState<string | null>(null);
  async function save(e: any) {
    e.preventDefault();
    const r = await execute(() => (editing ? api(`/api/admin/skills/${editing}`, { method: "PUT", body: JSON.stringify(form) }) : post("/api/admin/skills", form)), "Skill 已保存。", false);
    if (r !== undefined) { setEditing(null); setForm(blank); list.reload(); }
  }
  return (
    <>
      <p className="intro">Skill 是一段可复用的执行流程（按步骤写清楚先查什么、怎么筛、怎么判断）。采集定时器选了 Skill，模型就按它的流程执行。修改步骤会升版本，执行记录里能看到用的是哪一版。</p>
      <Failed error={list.error} />
      <table>
        <thead><tr><th>Skill</th><th>说明</th><th>版本</th><th>被引用</th><th>状态</th><th></th></tr></thead>
        <tbody>
          {list.value?.map((s) => (
            <tr key={s.id}><td>{s.name}<div className="muted">{s.skill_key}</div></td><td>{s.description || "—"}</td><td>v{s.version}</td>
              <td>{s.used_by} 个定时器</td><td>{s.enabled ? "启用" : "停用"}</td>
              <td className="actions"><button className="quiet" onClick={() => { setEditing(s.id); setForm({ skill_key: s.skill_key, name: s.name, description: s.description, body: s.body, enabled: s.enabled }); }}>编辑</button>
                <button className="quiet" disabled={busy || s.used_by > 0} title={s.used_by ? "还有定时器在用" : ""} onClick={async () => { if (!confirm(`删除 Skill「${s.name}」？`)) return; (await execute(() => api(`/api/admin/skills/${s.id}`, { method: "DELETE" }), "Skill 已删除。", false)) !== undefined && list.reload(); }}>删除</button></td></tr>
          ))}
        </tbody>
      </table>
      <form className="form" onSubmit={save}>
        <h4>{editing ? "编辑 Skill" : "新建 Skill"}</h4>
        <label>标识（小写字母、数字、-）<input required pattern="[a-z0-9_\-]+" value={form.skill_key} onChange={(e) => setForm({ ...form, skill_key: e.target.value })} placeholder="pharma-daily" /></label>
        <label>名称<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="创新药公司日报流程" /></label>
        <label>说明<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
        <label>执行流程（Markdown）<textarea required rows={12} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder={"1. 逐个公司检索过去 24 小时的交易所公告\n2. 再检索临床试验、医保谈判、BD 授权新闻\n3. 只保留可能影响长期价值的事件，删掉股价异动类快讯\n4. 每条写清楚涉及的公司和代码"} /></label>
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
