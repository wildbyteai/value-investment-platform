import React, { useEffect, useRef, useState } from "react";
export const dimensionName = (k: string) =>
  ({
    profit_quality: "盈利质量",
    financial_resilience: "财务韧性",
    business_model: "商业模式",
    governance: "治理与资本配置",
    growth_sustainability: "成长持续性",
    x_customer_retention: "客户留存",
  })[k] || k;
export const criterionName = (k: string) =>
  ({
    repeat_demand: "持续需求与续购",
    pricing_power: "定价能力",
    competitive_barrier: "竞争壁垒",
    concentration: "客户与供应商集中度",
    capital_intensity: "资本投入效率",
    related_party_transparency: "关联交易透明度",
    capital_allocation: "资本配置",
    disclosure: "信息披露",
    revenue_stability: "收入稳定性",
    incremental_sources: "增长来源",
    reinvestment_return: "再投资回报",
    retention: "客户留存",
  })[k] || k;
export const human = (x: any) => (x == null ? "待评估" : Number(x).toFixed(1));
export const when = (s: string) =>
  s ? new Date(s).toLocaleString("zh-CN") : "未留存";
export function ReferenceQuality({ value }: any) {
  if (!value) return null;
  return <section aria-label="参考经营分">
    <p>已覆盖维度参考分：{human(value.score_exact)}；加权覆盖 {(Number(value.coverage_exact) * 100).toFixed(0)}%。</p>
    <p className="muted">{value.meaning}</p>
    {value.missing_dimensions.length > 0 && <p>未覆盖：{value.missing_dimensions.map(dimensionName).join("、")}。</p>}
  </section>;
}
export function ReferenceValuation({ valuation: v, strategy: s }: any) {
  if (!v) return null;
  const names: Record<string, string> = {"company.quality_score":"已覆盖经营分", "company.coverage":"经营依据覆盖", "security.valuation_score":"参考估值分", "metrics.roe_ttm":"ROE", "metrics.cfo_profit_3y":"三年现金利润比", "metrics.net_debt_ebitda":"净债务/EBITDA"};
  const statuses: Record<string, string> = {PARTIAL:"部分可评估", MATCH:"参考条件满足", NO_MATCH:"参考条件未满足", RISK_EXCLUDED:"已确认风险排除", NOT_APPLICABLE:"策略不适用", SUSPENDED:"暂停评估", NO_RELEASE:"策略待发布"};
  return <section aria-label="参考估值与策略">
    <p><strong>参考PE：{v.status === "NOT_APPLICABLE" ? "不适用" : human(v.pe_exact)}；参考估值分：{human(v.valuation_exact)}</strong></p>
    <p className="muted">研究时点 {when(v.as_of)}；知识截止 {when(v.knowledge_cutoff)}。</p>
    {v.basis && <details><summary>参考计算依据</summary>
      <p>价格 {v.basis.raw_close} {v.basis.currency} · {v.basis.price_session}；普通股TTM利润 {v.basis.ordinary_profit_ttm} 人民币元（期间截至 {v.basis.profit_period_end || "见固定原文"}），股数 {v.basis.ordinary_shares} 股。</p>
      <p>股数结存日 {v.basis.shares_as_of || "未单列"}，覆盖至 {v.basis.shares_verified_through || "未单列"}；汇率 {v.basis.fx_per_cny ?? "缺失"} {v.basis.currency}/人民币。</p>
      {v.basis.converted_eps && <p>PE = 价格 / 换算EPS {v.basis.converted_eps}。</p>}
    </details>}
    {v.assumptions.length > 0 && <GapList values={v.assumptions} />}
    {v.missing_data.length > 0 && <GapList values={v.missing_data} />}
    {s && <>
      <h5>参考策略：{statuses[s.result] || s.result}{s.release_version != null && ` · 已发布版本 ${s.release_version}`}</h5>
      <p className="muted">{s.meaning}</p>
      <div className="table-scroll"><table><caption>逐项策略条件比较</caption><thead><tr><th>条件</th><th>实际值</th><th>门槛</th><th>结果</th></tr></thead>
        <tbody>{s.conditions.map((c: any) => <tr key={c.field}><th scope="row">{names[c.field] || c.field}</th><td>{c.actual == null ? "缺失或不适用" : Number(c.actual).toLocaleString("zh-CN", {maximumFractionDigits:4})}</td><td>{c.op === "gte" ? "≥" : "≤"} {c.expected}</td><td>{c.result == null ? "待补依据或核对适用性" : c.result ? "满足" : c.field === "company.coverage" ? "覆盖不足" : "未满足"}</td></tr>)}</tbody>
      </table></div>
      {s.gaps.length > 0 && <GapList values={s.gaps.map((g: string) => g.replace(/business_model|profit_quality|financial_resilience|growth_sustainability|governance/g, dimensionName))} />}
    </>}
  </section>;
}
export function Dialog({ title, children, close }: any) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const prior = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => {
      ref.current?.close();
      prior?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <div className="toolbar">
        <h2>{title}</h2>
        <button className="quiet" onClick={close}>
          关闭
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Diagnostic({ value }: any) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="text-button" onClick={() => setOpen(true)}>
        技术诊断
      </button>
      {open && (
        <Dialog title="技术诊断与元数据" close={() => setOpen(false)}>
          <p>当前对象的接口数据；业务依据在正文与评分解释中展示。</p>
          <pre>{JSON.stringify(value, null, 2)}</pre>
        </Dialog>
      )}
    </>
  );
}
export function GapList({ values = [] }: any) {
  return values.length ? (
    <ul className="gaps">
      {[...new Set(values)].map((g: string) => (
        <li key={g}>{g}</li>
      ))}
    </ul>
  ) : (
    <p className="muted">当前检查未报告缺口。</p>
  );
}
export function FinancialSummary({ data }: any) {
  return (
    <section>
      <h4>{data.original_statement ? "发行人财报原始科目" : "提供商财务指标参考"}</h4>
      <p>
        {data.report_rows}{" "}
        {data.original_statement
          ? "项核对科目；以下金额为人民币元，原值、单位与页码可在固定原文查看。标准评分及实际待补项见下方。"
          : "条记录；单位、统计范围与原始科目尚待核对，暂不用于标准财务评分。"}
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {(data.original_statement ? ["报告期", "资料日期（来源目录）", "合并净利润（元）", "经营现金流（元）", "归母净利润（元）", "归母权益（元）", "利息费用（元）"] : [
                "报告期",
                "提供商披露日",
                "利润原始字段",
                "EPS原始字段",
                "ROE原始字段",
                "股本原始字段",
                "CFO/利润原始字段",
              ]).map((t: string) => (
                <th key={t}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.periods.map((p: any) => (
              <tr key={p.stat_date}>
                <td>{p.stat_date}</td>
                <td>
                  {[
                    ...new Set(
                      Object.values(p.reports).map((r: any) => r.pub_date),
                    ),
                  ].join(" / ")}
                </td>
                {(data.original_statement ? ["consolidated_profit", "cfo", "parent_profit", "parent_equity", "interest_expense"] : ["netProfit", "epsTTM", "roeAvg", "totalShare", "CFOToNP"]).map(
                  (k) => (
                    <td key={k}>{p.values[k] ?? "缺失"}</td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.original_statement && data.available_metrics?.positive_cfo_year_share_3y != null && (
        <p>三年累计经营现金流 / 同口径合并净利润：{data.available_metrics.cfo_profit_3y ?? "不适用（同期三年合并利润合计非正）"}；
          正经营现金流年度比例：{data.available_metrics.positive_cfo_year_share_3y}。
          根据三年原始科目计算；完整评分仍取决于其余口径与经营依据。</p>
      )}
      {data.annual_net_profit_field_change_pct != null && (
        <p>
          三个完整年度利润同名字段首末变化{" "}
          {Number(data.annual_net_profit_field_change_pct).toFixed(2)}%
        </p>
      )}
      <details>
        <summary>口径与待补依据</summary>
        <p>{data.meaning}</p>
        <GapList values={data.missing_data} />
      </details>
    </section>
  );
}
export function ResearchResult({ run, read }: any) {
  return (
    <>
      <article>
        <h3>
          研究预览 · {run.status === "partial" ? "待补依据" : "本次计算完成"}
        </h3>
        <p>
          保存于 {when(run.created_at)}
          。记录当次所用来源与计算输入；不改变正式入选状态。
        </p>
        <ol className="stages">
          {run.result.stages.map((s: any) => (
            <li key={s.stage}>
              <strong>
                {
                  (
                    {
                      read_sources: "资料读取",
                      analyze: "字段比较",
                      score: "经营与估值评分",
                      strategy_preview: "策略预览",
                    } as any
                  )[s.stage]
                }
              </strong>
              <span
                className={
                  "badge " + (s.status === "completed" ? "success" : "")
                }
              >
                {s.status === "completed" ? "完成" : "待补依据"}
              </span>
              <p>{s.detail}</p>
            </li>
          ))}
        </ol>
        <Diagnostic value={run.manifest} />
      </article>
      {run.result.companies.map((c: any) => (
        <article key={c.company_id}>
          <h3>{c.company_name}</h3>
          {c.analysis.map((a: any) => (
            <section key={a.source_revision_id}>
              {a.kind === "financial_summary" ? (
                <FinancialSummary data={a} />
              ) : a.kind === "fx_summary" ? (
                <>
                  <h4>人民币与港币参考汇率</h4>
                  <p>{a.first_session} 至 {a.last_session}，{a.observations} 个日期；{a.last_session} 每1元人民币对应 {Number(a.last_rate).toFixed(6)} 港币。</p>
                  <p className="muted">{a.meaning}</p>
                </>
              ) : a.kind === "market_summary" ? (
                <>
                  <h4>参考日线区间统计</h4>
                  <p>
                    {a.first_session} 至 {a.last_session}，{a.observations}{" "}
                    个交易日；{a.first_close} → {a.last_close} {a.currency}
                    ，变化 {Number(a.change_pct).toFixed(2)}%
                  </p>
                  <p className="muted">未复权；{a.meaning}</p>
                </>
              ) : (
                <>
                  <h4>资料摘录</h4>
                  <p>{a.excerpt}</p>
                </>
              )}
              <button
                className="quiet"
                onClick={() => read(a.source_item_id, a.source_revision_id)}
              >
                阅读此次固定原文
              </button>
            </section>
          ))}
          <h4>经营质量：{human(c.quality.quality_score)}</h4>
          <ReferenceQuality value={c.quality.reference_quality} />
          <GapList values={c.quality.missing_data} />
          {c.judgment_proposals?.length > 0 && <section>
            <h4>本次固定的经营研判建议</h4>
            <p className="muted">AI依据原文提出，待确认；未计入上述评分，历史建议保持当时结果。</p>
            {c.judgment_proposals.map((p: any) => <section key={p.revision_id}>
              <h5>{dimensionName(p.dimension)} · {criterionName(p.value.criterion)} · 建议{p.value.grade}档</h5>
              <p>{p.value.reason}</p><p className="muted">局限与反证：{p.value.limitations}</p>
              {p.evidence.map((e: any, i: number) => <div key={i}>
                <details><summary>{e.relation === "contradicts" ? "阅读反证或限制条件" : "阅读支持证据"}</summary><blockquote>{e.quote}</blockquote></details>
                <button className="quiet" onClick={() => read(e.item_id,e.source_revision_id)}>阅读研判固定原文</button>
              </div>)}
            </section>)}
          </section>}
          <div className="securities">
            {c.securities.map((s: any) => (
              <section key={s.security_id}>
                <h4>
                  {s.ticker} · {s.market === "HK" ? "港股" : "A股"}
                </h4>
                <p>
                  {s.latest_quote
                    ? `参考价 ${s.latest_quote.raw_close} ${s.currency} · ${s.latest_quote.session}`
                    : "行情待接入"}
                </p>
                <p>
                  正式估值分：{human(s.valuation.valuation_score)}；正式规则预览：
                  {s.strategy.result === "UNKNOWN"
                    ? "待评估"
                    : s.strategy.result === "MATCH"
                      ? "满足条件"
                      : "未满足条件"}
                </p>
                <ReferenceValuation valuation={s.valuation.reference_valuation} strategy={s.valuation.reference_strategy} />
                <GapList values={s.gaps} />
              </section>
            ))}
          </div>
          <Diagnostic value={c} />
        </article>
      ))}
    </>
  );
}
export function CompareRuns({ left, right }: any) {
  const describe = (c: any) =>
    c
      ? `${c.analysis.length}份资料；财务字段 ${c.analysis.filter((a: any) => a.kind === "financial_summary").reduce((n: number, a: any) => n + a.report_rows, 0)} 条；加权覆盖 ${(c.quality.coverage * 100).toFixed(0)}%`
      : "此快照未包含该公司";
  const quote = (s: any) =>
    s?.latest_quote
      ? `${s.latest_quote.raw_close} ${s.currency}（${s.latest_quote.session}）`
      : "未取得参考价";
  const strategy = (s: any) =>
    s
      ? { UNKNOWN: "待评估", MATCH: "满足条件", NO_MATCH: "未满足条件" }[
          s.strategy.result
        ] || s.strategy.result
      : "未记录";
  return (
    <article>
      <h3>已保存快照比较</h3>
      <p>两份已保存结果直接比较，不使用当前输入重算历史。</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>公司 / 证券</th>
              <th>{when(left.created_at)}</th>
              <th>{when(right.created_at)}</th>
            </tr>
          </thead>
          <tbody>
            {[
              ...new Set(
                [...left.result.companies, ...right.result.companies].map(
                  (c: any) => c.company_id,
                ),
              ),
            ].map((id: string) => {
              const a = left.result.companies.find(
                  (c: any) => c.company_id === id,
                ),
                b = right.result.companies.find(
                  (c: any) => c.company_id === id,
                );
              return (
                <React.Fragment key={id}>
                  <tr>
                    <th>{a?.company_name || b?.company_name}经营质量</th>
                    <td>{human(a?.quality.quality_score)}</td>
                    <td>{human(b?.quality.quality_score)}</td>
                  </tr>
                  <tr>
                    <td>当次资料与依据进度</td>
                    <td>{describe(a)}</td>
                    <td>{describe(b)}</td>
                  </tr>
                  <tr>
                    <td>当次已覆盖维度参考分</td>
                    <td>{a?.quality.reference_quality ? human(a.quality.reference_quality.score_exact) : "旧快照未留存"}</td>
                    <td>{b?.quality.reference_quality ? human(b.quality.reference_quality.score_exact) : "旧快照未留存"}</td>
                  </tr>
                  <tr>
                    <td>当次待补依据</td>
                    <td>
                      <GapList values={a?.quality.missing_data} />
                    </td>
                    <td>
                      <GapList values={b?.quality.missing_data} />
                    </td>
                  </tr>
                  {[
                    ...new Set(
                      [...(a?.securities || []), ...(b?.securities || [])].map(
                        (s: any) => s.security_id,
                      ),
                    ),
                  ].map((sid: string) => {
                    const x = a?.securities.find(
                        (s: any) => s.security_id === sid,
                      ),
                      y = b?.securities.find((s: any) => s.security_id === sid);
                    return (
                      <React.Fragment key={sid}>
                        <tr>
                          <td>{x?.ticker || y?.ticker}参考价</td>
                          <td>{quote(x)}</td>
                          <td>{quote(y)}</td>
                        </tr>
                        <tr>
                          <td>{x?.ticker || y?.ticker}估值 / 策略预览</td>
                          <td>
                            {human(x?.valuation.valuation_score)} /{" "}
                            {strategy(x)}
                          </td>
                          <td>
                            {human(y?.valuation.valuation_score)} /{" "}
                            {strategy(y)}
                          </td>
                        </tr>
                        <tr>
                          <td>{x?.ticker || y?.ticker}参考PE / 参考估值分</td>
                          <td>{x?.valuation.reference_valuation ? `${human(x.valuation.reference_valuation.pe_exact)} / ${human(x.valuation.reference_valuation.valuation_exact)}` : "旧快照未留存"}</td>
                          <td>{y?.valuation.reference_valuation ? `${human(y.valuation.reference_valuation.pe_exact)} / ${human(y.valuation.reference_valuation.valuation_exact)}` : "旧快照未留存"}</td>
                        </tr>
                      </React.Fragment>
                    );
                  })}
                  <tr>
                    <td>当次模板与输入</td>
                    <td>
                      {a?.quality.template.levels_applied.join(" → ")}
                      <Diagnostic
                        value={left.manifest.calculation_refs?.find(
                          (c: any) => c.company_id === id,
                        )}
                      />
                    </td>
                    <td>
                      {b?.quality.template.levels_applied.join(" → ")}
                      <Diagnostic
                        value={right.manifest.calculation_refs?.find(
                          (c: any) => c.company_id === id,
                        )}
                      />
                    </td>
                  </tr>
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}
