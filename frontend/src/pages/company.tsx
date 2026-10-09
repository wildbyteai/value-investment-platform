// 公司档案：公司、今日概览、研究快照、我的自选与笔记。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
import { Ctx, ZONE, pct, num, signed, time, any, useLoad, Failed, ZoneBadge, Check, short, tone, Kpi } from "../components/common";
import { Diagnostic, GapList, FinancialSummary, ResearchResult, ReferenceQuality, ReferenceValuation, CompareRuns, Dialog, dimensionName, criterionName, human, when } from "../components/ui";
import { AuthorJudgment, Judgment } from "../components/judgments";
import { TemplateEditor } from "../components/template";
export const companyTabs = [
  "经营质量与待补依据",
  "财务与估值依据",
  "资料与研判",
  "评分规则",
];
export function CompanyPanel({
  company: c,
  judgments,
  watchIds,
  toggle,
  busy,
  allow,
  execute,
  read,
  error,
  research,
}: any) {
  const [index, setIndex] = useState(0);
  const [author, setAuthor] = useState<any>();
  const [financials, setFinancials] = useState<any>();
  async function startAuthor() {
    const docs = await execute(
      () =>
        Promise.all(
          c.timeline.items.map((it: any) => api(`/api/intake/items/${it.id}`)),
        ),
      undefined,
      false,
    );
    if (docs) setAuthor(docs.filter((d: any) => d.original_text && d.revision));
  }
  async function viewFinancials() {
    setIndex(1);
    const d = await execute(
      async () => {
        const runs = await api("/api/research/runs");
        if (!runs.length) return [];
        const run = await api(`/api/research/runs/${runs[0].id}`);
        return (
          run.result.companies
            .find((x: any) => x.company_id === c.id)
            ?.analysis.filter((a: any) => a.kind === "financial_summary") || []
        );
      },
      undefined,
      false,
    );
    if (d) setFinancials(d);
  }
  return (
    <>
      <article>
        <h3>{c.name}</h3>
        <p>
          经营质量：{human(c.score.quality_score)}。依据{" "}
          {c.score.known_dimensions.length}/
          {Object.keys(c.score.dimensions).length} 个维度，加权覆盖{" "}
          {(c.score.coverage * 100).toFixed(0)}%。
        </p>
        <ReferenceQuality value={c.score.reference_quality} />
        <GapList values={c.score.missing_data.slice(0, 2)} />
        {allow("analysis.override") && (
          <button className="primary" disabled={busy || !c.catalog.length} onClick={startAuthor}>
            补充一项真实研判
          </button>
        )}
        <div className="securities">
          {c.score.securities.map((s: any) => (
            <section key={s.security_id}>
              <h4>
                {s.market === "HK" ? "港股" : "A股"} {s.ticker}
              </h4>
              <p className="quote">
                {s.latest_quote
                  ? `${s.latest_quote.raw_close} ${s.currency}`
                  : "行情待接入"}
              </p>
              {s.latest_quote ? (
                <p className="muted">
                  {s.latest_quote.session}
                  ，未复权参考日线价；尚未核验为正式策略用价。
                </p>
              ) : (
                <p className="muted">
                  A/H共用公司基本面；本证券需独立行情与汇率。
                </p>
              )}
              <p>
                正式PE：{human(s.pe_ttm)}；正式估值分：{human(s.valuation_score)}
              </p>
              <ReferenceValuation valuation={s.reference_valuation} strategy={s.reference_strategy} />
              <p className="muted">正式状态：暂不提供，封存评估尚未就绪。</p>
              {allow("watchlist.own") && (
                <button
                  disabled={busy || watchIds === null}
                  onClick={() => toggle(s)}
                >
                  {watchIds === null
                    ? "自选状态待读取"
                    : watchIds.has(s.security_id)
                      ? "已加入自选 · 点击移除"
                      : "加入自选"}
                </button>
              )}
              <details>
                <summary>估值依据与缺口</summary>
                <GapList values={s.missing_data} />
                {s.share_capital && (
                  <>
                    <p>已核对股数：{s.share_capital.ordinary_shares} 股；结存日 {s.share_capital.shares_as_of}，证据覆盖至 {s.share_capital.ordinary_shares_verified_through}。覆盖之后需取得新的依据。</p>
                    {s.share_capital.classes.map((row: any) => (
                      <p key={row.class_key} className="muted">{row.class_key}：在外 {row.outstanding_shares} 股，库存 {row.treasury_shares} 股，已发行 {row.issued_shares} 股。</p>
                    ))}
                  </>
                )}
                {s.basis && (
                  <p>
                    利润 {s.basis.ordinary_profit_ttm} / 股本{" "}
                    {s.basis.ordinary_shares}，EPS {s.basis.eps}，汇率{" "}
                    {s.basis.fx}；PE = 收盘价 {s.basis.raw_final_close} /
                    换算EPS {s.basis.converted_eps}。
                  </p>
                )}
                <Diagnostic value={s} />
              </details>
            </section>
          ))}
        </div>
      </article>
      <div className="tabs" role="tablist" aria-label="公司研究内容">
        {companyTabs.map((label, i) => (
          <button
            key={label}
            role="tab"
            aria-selected={index === i}
            aria-controls={"company-panel-" + i}
            id={"company-tab-" + i}
            tabIndex={index === i ? 0 : -1}
            onKeyDown={(e) => {
              if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
                e.preventDefault();
                const n =
                  e.key === "Home"
                    ? 0
                    : e.key === "End"
                      ? 3
                      : (i + (e.key === "ArrowRight" ? 1 : 3)) % 4;
                setIndex(n);
                document.getElementById("company-tab-" + n)?.focus();
                if (n === 1) viewFinancials();
              }
            }}
            onClick={() => (i === 1 ? viewFinancials() : setIndex(i))}
          >
            {label}
          </button>
        ))}
      </div>
      <article
        role="tabpanel"
        id={"company-panel-" + index}
        aria-labelledby={"company-tab-" + index}
      >
        {index === 0 && (
          <>
            <h3>经营质量与待补依据</h3>
            <GapList values={c.score.missing_data} />
            {Object.entries(c.score.dimensions).map(([d, v]: any) => (
              <section key={d} className="dimension">
                <h4>
                  {dimensionName(d)}：{human(v.score)}{" "}
                  <span className="muted">
                    权重{" "}
                    {(Number(c.score.template.weights[d]) * 100).toFixed(0)}%
                  </span>
                </h4>
                <p>
                  基准 {human(v.baseline)}；事件贡献{" "}
                  {human(v.event_contribution)}；来源{" "}
                  {c.score.template.field_origins?.[d]?.baseline ||
                    c.score.template.origins[d]}
                </p>
                {v.reason && <p>{v.reason}</p>}
                {v.criteria?.map((q: any) => (
                  <p key={q.key}>
                    {criterionName(q.key)}：
                    {q.status === "valid" ? `${q.grade}档` : "待补"} {q.reason}
                  </p>
                ))}
                <Diagnostic value={v} />
              </section>
            ))}
          </>
        )}
        {index === 1 && (
          <>
            <h3>财务与估值依据</h3>
            <p>
              财务字段来自最近已保存预览，期间与提供商披露日期分别列示。新资料需生成新预览。
            </p>
            {financials === undefined ? (
              <p role="status">读取财务参考…</p>
            ) : financials.length ? (
              financials.map((f: any) => (
                <FinancialSummary key={f.source_revision_id} data={f} />
              ))
            ) : (
              <p>尚无保存的财务字段比较。</p>
            )}
            <GapList values={c.score.missing_data} />
            <button onClick={research}>
              查看 / 生成研究预览
            </button>
          </>
        )}
        {index === 2 && (
          <>
            <h3>资料与研判</h3>
            {c.timeline.items.map((it: any) => (
              <p key={it.id}>
                <button
                  className="link"
                  disabled={busy}
                  onClick={() => read(it.id)}
                >
                  {it.title}
                </button>
              </p>
            ))}
            {judgments.length ? (
              judgments.map((j: any) => (
                <Judgment
                  key={j.slot_key}
                  j={j}
                  catalog={c.catalog}
                  editable={allow("analysis.override")}
                  execute={execute}
                />
              ))
            ) : (
              <p>尚无可用研判。先阅读固定原文，再按评价项补充。</p>
            )}
            {allow("analysis.override") && (
              <button className="primary"
                disabled={busy || !c.catalog.length}
                onClick={startAuthor}
              >
                补充真实研判
              </button>
            )}
            <button onClick={research}>
              生成新的研究预览
            </button>
          </>
        )}
        {index === 3 && (
          <TemplateEditor
            company={c}
            template={c.score.template}
            allow={allow}
            execute={execute}
          />
        )}
      </article>
      {author && (
        <AuthorJudgment
          company={c}
          catalog={c.catalog}
          documents={author}
          execute={execute}
          error={error}
          close={() => setAuthor(null)}
        />
      )}
    </>
  );
}
export function ResearchPage({
  data,
  busy,
  read,
  execute,
  allow,
  runKey,
  nextKey,
}: any) {
  const [detail, setDetail] = useState(data.detail);
  const [other, setOther] = useState<any>();
  const [compareId, setCompareId] = useState("");
  return (
    <>
      <p>
        根据已取得资料生成新的研究预览，记录当次输入与口径。预览不改变正式入选状态。
      </p>
      {allow("analysis.override") && (
        <button className="primary"
          disabled={busy}
          onClick={async () => {
            const r = await execute(
              () =>
                post("/api/research/runs", {}, { "Idempotency-Key": runKey }),
              "研究预览已保存，请核对完成阶段与待补依据。",
            );
            if (r) {
              setDetail(r);
              nextKey();
            }
          }}
        >
          生成新的研究预览
        </button>
      )}
      {data.runs.length ? (
        <label>
          已保存快照
          <select
            value={detail?.id || ""}
            disabled={busy}
            onChange={async (e) => {
              const d = await execute(
                () => api(`/api/research/runs/${e.target.value}`),
                undefined,
                false,
              );
              if (d) {
                setDetail(d);
                setOther(null);
                setCompareId("");
              }
            }}
          >
            {data.runs.map((r: any) => (
              <option key={r.id} value={r.id}>
                {when(r.created_at)} ·{" "}
                {r.status === "partial" ? "待补依据" : "完成"}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <p>尚无研究快照。</p>
      )}
      {detail && (
        <>
          <label>
            比较另一份已保存快照
            <select
              value={compareId}
              onChange={(e) => setCompareId(e.target.value)}
            >
              <option value="">请选择</option>
              {data.runs
                .filter((r: any) => r.id !== detail.id)
                .map((r: any) => (
                  <option key={r.id} value={r.id}>
                    {when(r.created_at)}
                  </option>
                ))}
            </select>
          </label>
          <button
            disabled={!compareId || busy}
            onClick={async () => {
              const d = await execute(
                () => api(`/api/research/runs/${compareId}`),
                undefined,
                false,
              );
              if (d) setOther(d);
            }}
          >
            比较已保存结果
          </button>
          {other && <CompareRuns left={detail} right={other} />}
          <ResearchResult run={detail} read={read} />
        </>
      )}
    </>
  );
}
export function Mine({ data, busy, execute, openCompany }: any) {
  const [id, setId] = useState(data.companies[0]?.id || "");
  const [note, setNote] = useState("");
  return (
    <>
      <article>
        <h3>我的证券自选</h3>
        {data.watch.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>证券</th>
                  <th>参考报价</th>
                  <th>正式状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {data.watch.map((w: any) => (
                  <tr key={w.security_id}>
                    <td>
                      {w.market === "HK" ? "港股" : "A股"} {w.ticker}
                    </td>
                    <td>
                      {(() => {
                        const q = data.companies
                          .find((c: any) => c.id === w.company_id)
                          ?.score.securities.find(
                            (s: any) => s.security_id === w.security_id,
                          )?.latest_quote;
                        return q
                          ? `${q.raw_close} ${q.currency}（${q.session}）`
                          : "行情待接入";
                      })()}
                    </td>
                    <td>暂不提供正式入选状态</td>
                    <td>
                      <button
                        onClick={() => openCompany(w.company_id)}
                      >
                        查看公司与参考报价
                      </button>
                      <button
                        disabled={busy}
                        onClick={() =>
                          execute(
                            () =>
                              api(`/api/me/watchlist/${w.security_id}`, {
                                method: "DELETE",
                              }),
                            "已取消此证券自选。",
                          )
                        }
                      >
                        取消自选
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>暂无自选，在公司页分别加入A股或港股。</p>
        )}
      </article>
      <article>
        <h3>研究笔记</h3>
        <label>
          公司
          <select value={id} onChange={(e) => setId(e.target.value)}>
            {data.companies.map((c: any) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          笔记内容
          <textarea value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <button className="primary"
          disabled={busy || !note.trim() || !id}
          onClick={async () => {
            const r = await execute(
              () => post("/api/me/notes", { company_id: id, body: note }),
              "笔记已保存。",
            );
            if (r) setNote("");
          }}
        >
          保存笔记
        </button>
        {data.notes.map((n: any) => (
          <section key={n.id}>
            <h4>
              {data.companies.find((c: any) => c.id === n.company_id)?.name}
            </h4>
            <p className="note">{n.body}</p>
          </section>
        ))}
      </article>
    </>
  );
}
(() => { try { document.documentElement.dataset.theme = localStorage.getItem("vip-theme") || "light"; } catch {} })();
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
// 今日概览：每家公司一张卡片，点进公司页继续研究。
export function TodayPage({ data, busy, openCompany, navigate }: any) {
  return (
    <>
              <p className="intro">
                真实资料研究预览。先看公司与关键缺口，再阅读依据、补充研判。
              </p>
              <div className="overview">
                {data.companies.map((c: any) => (
                  <article key={c.id}>
                    <h3>{c.name}</h3>
                    <span
                      className={
                        "badge " +
                        (c.score.quality_score == null ? "" : "success")
                      }
                    >
                      {c.score.quality_score == null
                        ? c.score.reference_quality?.score_exact != null ? "真实依据 · 部分可评估" : "资料可读 · 经营待评估"
                        : "经营依据可评估"}
                    </span>
                    <p>
                      经营质量：{human(c.score.quality_score)}；
                      {c.timeline.items.length} 份关联资料
                    </p>
                    {c.score.reference_quality?.score_exact != null && <p>已覆盖经营分 {human(c.score.reference_quality.score_exact)} · 覆盖 {(c.score.coverage * 100).toFixed(0)}%</p>}
                    <GapList values={c.score.missing_data.slice(0, 2)} />
                    <button className="primary"
                      disabled={busy}
                      onClick={() => {
                        openCompany(c.id);
                      }}
                    >
                      继续研究这家公司
                    </button>
                  </article>
                ))}
              </div>
              {!data.companies.length && (
                <p>
                  暂无有权读取且已关联的公司资料。请由数据管理员接入获许可来源。
                </p>
              )}
              <h3>最近已保存研究</h3>
              {data.runs.length ? (
                <p>
                  {when(data.runs[0].created_at)} ·{" "}
                  {data.runs[0].status === "partial"
                    ? "待补依据"
                    : "本次计算完成"}{" "}
                  <button
                    onClick={() => navigate("research")}
                  >
                    查看快照
                  </button>
                </p>
              ) : (
                <p>尚无研究快照；阅读并研判后可生成预览。</p>
              )}
            </>
  );
}
// 公司：选择一家公司，看经营、财务估值、资料研判与资讯主线。
export function CompaniesPage({ data, selected, setSelected, watchIds, toggle, busy, allow, execute, read, error, navigate }: any) {
  return (
    <>
              <label>
                研究公司
                <select
                  value={selected || data.companies[0]?.id || ""}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {data.companies.map((c: any) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              {data.companies
                .filter(
                  (c: any) => c.id === (selected || data.companies[0]?.id),
                )
                .map((c: any) => (
                  <CompanyPanel
                    key={c.id}
                    company={c}
                    judgments={data.judgments.filter(
                      (j: any) => j.company_id === c.id,
                    )}
                    watchIds={watchIds}
                    toggle={toggle}
                    busy={busy}
                    allow={allow}
                    execute={execute}
                    read={read}
                    error={error}
                    research={() => navigate("research")}
                  />
                ))}
              {!!data.companies.length && (
                <CompanyMainline companyId={selected || data.companies[0].id} />
              )}
              {!data.companies.length && <p>当前工作区暂无可研究公司。</p>}
            </>
  );
}
