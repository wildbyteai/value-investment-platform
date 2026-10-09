// 资讯雷达：事件与关联、原始资料与研判。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
import { Ctx, ZONE, pct, num, signed, time, any, useLoad, Failed, ZoneBadge, Check, short, tone, Kpi } from "../components/common";
import { Diagnostic, GapList, FinancialSummary, ResearchResult, ReferenceQuality, ReferenceValuation, CompareRuns, Dialog, dimensionName, criterionName, human, when } from "../components/ui";
import { AuthorJudgment, Judgment } from "../components/judgments";
import { TemplateEditor } from "../components/template";
export function NewsRadar({ allow, busy, execute }: Ctx) {
  const [filter, setFilter] = useState("");
  const events = useLoad<any[]>(`/api/news/events?limit=80${filter ? `&status=${filter}` : ""}`);
  const companies = useLoad<any[]>("/api/companies");
  const [selId, setSelId] = useState<string>("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
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
  const waitingIds = (es: any[]) => es.flatMap((e) => e.links.filter((l: any) => l.status === "proposed").map((l: any) => l.id));
  const pickedEvents = list.filter((e) => picked.has(e.id));
  const reviewable = list.filter((e) => e.links.some((l: any) => l.status === "proposed"));
  const allPicked = reviewable.length > 0 && reviewable.every((e) => picked.has(e.id));
  function toggle(id: string) {
    const next = new Set(picked);
    next.has(id) ? next.delete(id) : next.add(id);
    setPicked(next);
  }
  async function batch(ids: string[], action: "confirm" | "reject") {
    if (!ids.length) return;
    const verb = action === "confirm" ? "确认" : "驳回";
    const r = await execute(() => post("/api/news/links/review-batch", { action, link_ids: ids }), (r: any) => {
      const alerts = r.alerts?.length ? `，触发 ${r.alerts.length} 条告警` : "";
      const skipped = r.skipped?.length
        ? `；${r.skipped.length} 个没处理（${r.skipped.slice(0, 3).map((x: any) => `${x.company}：${x.reason}`).join("；")}），请逐条修改后再确认`
        : "";
      return `已${verb} ${r.done.length} 个关联${alerts}${skipped}`;
    }, false);
    if (r === undefined) return;
    setPicked(new Set());
    events.reload();
  }
  const ups = list.filter((e) => e.impact_score != null && e.impact_score >= 0.3).length;
  const downs = list.filter((e) => e.impact_score != null && e.impact_score <= -0.3).length;
  const items = list.reduce((n, e) => n + (e.item_count || 0), 0);
  return (
    <>
      <p className="intro">每条资讯先合并成事件，再判断关联哪些公司、关联多紧（关联度 0–1）、影响多大（影响分 −1 到 1）。AI 先预判，研究员确认、批量确认或修改后才进入告警。</p>
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
              {canReview && picked.size > 0 && (
                <>
                  <span className="muted small">已选 {picked.size} 个事件</span>{" "}
                  <button className="primary small" disabled={busy} onClick={() => batch(waitingIds(pickedEvents), "confirm")}>批量确认 AI 结果</button>{" "}
                  <button className="small" disabled={busy} onClick={() => batch(waitingIds(pickedEvents), "reject")}>批量驳回</button>{" "}
                </>
              )}
              {canScore && (
                <button className="small" disabled={busy} onClick={() => act(() => post("/api/news/score", {}), "已对待处理事件重新打分。")}>
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
                  <tr>
                    {canReview && <th><input type="checkbox" aria-label="全选待确认事件" checked={allPicked}
                      onChange={() => setPicked(allPicked ? new Set() : new Set(reviewable.map((e) => e.id)))} /></th>}
                    <th>时间</th><th>事件</th><th>关联公司</th><th>关联度</th><th>影响分</th><th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((e) => {
                    const top = Math.max(0, ...e.links.map((l: any) => Number(l.relevance) || 0));
                    const waiting = e.links.some((l: any) => l.status === "proposed");
                    return (
                      <tr key={e.id} aria-selected={sel?.id === e.id} onClick={() => setSelId(e.id)}>
                        {canReview && <td onClick={(ev) => ev.stopPropagation()}>
                          {waiting && <input type="checkbox" aria-label={`选择 ${e.title}`} checked={picked.has(e.id)} onChange={() => toggle(e.id)} />}
                        </td>}
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
              <div className="sec-label">
                关联公司
                {canReview && waitingIds([sel]).length > 1 && (
                  <button className="primary small" style={{ float: "right" }} disabled={busy} onClick={() => batch(waitingIds([sel]), "confirm")}>
                    全部确认 AI 结果
                  </button>
                )}
              </div>
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
export function LinkCard({ l, canReview, busy, review, companies }: any) {
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
            <button className="primary" disabled={busy} onClick={() => review({ action: "confirm", impact, relevance, company_id: company || null }, "已确认关联；落进击球区会立即告警。")}>确认关联</button>
          )}
          {l.status !== "rejected" && (
            <button disabled={busy} onClick={() => review({ action: "reject" }, "已驳回该关联。")}>驳回</button>
          )}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 击球区
// 原始资料与研判：已保存资料的列表与当前研判。
export function RawNewsPage({ data, busy, read, allow, execute, navigate }: any) {
  return (
    <>
              <p>
                资料的公布 /
                修订时间与系统取得时间分别展示，百科修订不等同公司事件。
              </p>
              {data.items.map((it: any) => (
                <article key={it.id}>
                  <div className="meta">
                    <span>{it.source_name}</span>
                    <span>资料日期 {it.publication_date || "未知"}</span>
                  </div>
                  <h3>{it.title}</h3>
                  <p>{it.summary_text || "暂无摘要"}</p>
                  <p className="muted">系统取得 {when(it.observed_at)}</p>
                  <button
                    disabled={busy}
                    onClick={() => read(it.id)}
                  >
                    {it.body_state === "available"
                      ? "阅读原文与来源"
                      : "阅读摘要与来源"}
                  </button>
                </article>
              ))}
              {!data.items.length && (
                <p>尚无可读资料。请接入具有保存与分析许可的来源。</p>
              )}
              <h3>当前研判</h3>
              {data.judgments.map((j: any) => (
                <Judgment
                  key={j.slot_key}
                  j={j}
                  editable={allow("analysis.override")}
                  execute={execute}
                />
              ))}
              <button onClick={() => navigate("companies")}>
                到公司页核对评价项并补充研判
              </button>
            </>
  );
}
