// 策略：击球区与策略规则。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
import { Ctx, ZONE, pct, num, signed, time, any, useLoad, Failed, ZoneBadge, Check, short, tone, Kpi } from "../components/common";
import { Diagnostic, GapList, FinancialSummary, ResearchResult, ReferenceQuality, ReferenceValuation, CompareRuns, Dialog, dimensionName, criterionName, human, when } from "../components/ui";
import { AuthorJudgment, Judgment } from "../components/judgments";
import { TemplateEditor } from "../components/template";
export const fieldName = (k: string) =>
  ({
    "company.quality_score": "经营质量分",
    "company.coverage": "加权覆盖度",
    "security.valuation_score": "证券估值分",
    "metrics.roe_ttm": "TTM ROE",
    "metrics.cfo_profit_3y": "三年累计CFO/利润",
    "metrics.net_debt_ebitda": "净负债/EBITDA",
  })[k] || k;
export function StrategyPage({ data, allow, busy, execute }: any) {
  const rule = data.rule;
  const [threshold, setThreshold] = useState(
    rule.rules.enter.all.find((r: any) => r.field === "company.quality_score")
      .value,
  );
  const [preview, setPreview] = useState<any>();
  const [confirm, setConfirm] = useState(false);
  const [historical, setHistorical] = useState<any>();
  return (
    <>
      <article>
        <h3>{rule.rules.name}</h3>
        <p>
          {rule.version ? `已发布版本 ${rule.version}` : "参考基准，尚未发布"}
        </p>
        <div className="securities">
          {["enter", "retain"].map((k) => (
            <section key={k}>
              <h4>{k === "enter" ? "准入门槛" : "保持门槛"}</h4>
              {rule.rules[k].all.map((r: any) => (
                <p key={r.field}>
                  {fieldName(r.field)} {r.op === "gte" ? "≥" : "≤"} {r.value}
                </p>
              ))}
            </section>
          ))}
        </div>
        <details>
          <summary>适用范围、时效与硬风险</summary>
          <p>
            市场：{rule.rules.universe.markets.join(" / ")}；排除行业：
            {rule.rules.universe.exclude_sector_groups.join(" / ")}。
          </p>
          <p>
            必需维度：
            {rule.rules.quality_gates.required_dimensions
              .map(dimensionName)
              .join("、")}
            ；经营判断最长 {rule.rules.quality_gates.baseline_max_age_days}{" "}
            天；财务按报告义务。
          </p>
          <p>
            已确认欺诈、重大持续经营、债务违约或退市风险按目标证券排除；参考日线不能替代FINAL评估价格。
          </p>
        </details>
        <Diagnostic value={rule.rules} />
      </article>
      {allow("strategy.simulate") && (
        <article>
          <h3>规则草稿</h3>
          <p>只修改经营质量准入门槛，其他规则保留当前发布值。</p>
          <label>
            经营质量准入门槛
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={threshold}
              onChange={(e) => {
                setThreshold(e.target.value);
                setPreview(null);
                setConfirm(false);
              }}
            />
          </label>
          <button
            disabled={busy || threshold === ""}
            onClick={async () => {
              const r = await execute(
                () =>
                  post("/api/strategy/simulate", {
                    quality_threshold: threshold,
                    expected_version: rule.version,
                  }),
                undefined,
                false,
              );
              if (r) setPreview(r);
            }}
          >
            进行模拟测算
          </button>
          {preview && (
            <>
              <h4>
                当前版本 → 草稿：
                {
                  rule.rules.enter.all.find(
                    (g: any) => g.field === "company.quality_score",
                  ).value
                }{" "}
                → {threshold}
              </h4>
              {preview.results.map((r: any) => (
                <section key={r.security_id}>
                  <p>
                    {r.company} {r.ticker}：
                    {r.status === "risk_excluded"
                      ? "风险排除"
                      : r.status === "suspended"
                        ? "暂停评估"
                        : r.status === "not_applicable"
                          ? "不适用"
                          : r.passes == null
                            ? "待评估"
                            : r.passes
                              ? "满足条件"
                              : "未满足条件"}
                  </p>
                  <GapList values={r.gaps} />
                  <details>
                    <summary>逐项数值条件</summary>
                    {r.conditions.map((q: any) => (
                      <p key={q.field}>
                        {fieldName(q.field)}：{q.actual ?? "缺失"}{" "}
                        {q.op === "gte" ? "≥" : "≤"} {q.expected}；
                        {q.result === null
                          ? "待评估"
                          : q.result
                            ? "满足"
                            : "未满足"}
                      </p>
                    ))}
                  </details>
                </section>
              ))}
              <Diagnostic value={preview.rules} />
              {allow("strategy.publish") &&
                (confirm ? (
                  <>
                    <p className="notice">
                      发布所见草稿与模拟输入。新版本发布后仍需正式评估，模拟满足不代表入选。
                    </p>
                    <button
                      disabled={busy}
                      onClick={async () => {
                        const r = await execute(
                          () =>
                            post("/api/strategy/publish", {
                              quality_threshold: threshold,
                              expected_version: preview.expected_version,
                              simulation_token: preview.simulation_token,
                            }),
                          "策略新版本已发布，正式评估尚未生成。",
                        );
                        if (r) {
                          setPreview(null);
                          setConfirm(false);
                        }
                      }}
                    >
                      确认发布策略
                    </button>
                    <button className="quiet" onClick={() => setConfirm(false)}>
                      取消
                    </button>
                  </>
                ) : (
                  <button disabled={busy} onClick={() => setConfirm(true)}>
                    发布策略新版本
                  </button>
                ))}
            </>
          )}
        </article>
      )}
      <h3>正式评估</h3>
      <p>研究预览与正式评估分别保存。缺少依据时，正式结果也会保留为待补资料；空记录不能推断未入选。</p>
      {!data.seals.available && <p role="status">{data.seals.reason}</p>}
      {data.seals.available && data.seals.rows.length === 0 && <p>尚无已排期的正式评估。需要先核验挂牌日历、最终收盘政策和已发布策略。</p>}
      {data.seals.rows.map((r: any) => <article key={r.seal_id}>
        <h4>{r.ticker} · {r.currency} · {r.market_session}</h4>
        <p>{({sealed:"已封存",provisional:"截止时间未到",ready_to_seal:"正在冻结",blocked_safety:"权限、关联或模板已变化，暂停应用",session_due:"等待截止"} as Record<string,string>)[r.phase] || "等待处理"}
          {r.validity === "UNKNOWN" ? " · 待补资料" : r.validity === "VALID" ? " · 依据有效" : ""}
          {r.application === "superseded" ? " · 历史结果，未应用" : r.membership ? ` · 当前版本状态 ${r.membership}` : ""}</p>
        <p>资料截止：{new Date(r.knowledge_cutoff).toLocaleString()}；{r.generated_at ? `生成：${new Date(r.generated_at).toLocaleString()}` : "尚未生成"}</p>
        {r.gaps.length > 0 && <ul>{r.gaps.map((g:string) => <li key={g}>{g}</li>)}</ul>}
        {r.evaluation_id && <button className="quiet" onClick={async () => {
          const d=await execute(() => api(`/api/strategy/evaluations/${r.evaluation_id}`),undefined,false);
          if(d)setHistorical(d);
        }}>查看固定依据与解释</button>}
      </article>)}
      <h3>正式变化记录</h3>
      {data.changes.map((t: any) => (
        <article key={t.id}>
          <p>
            {t.session}：{t.from} → {t.to}（{t.reason}）
          </p>
          <button
            className="quiet"
            onClick={async () => {
              const d = await execute(
                () => api(`/api/strategy/evaluations/${t.evaluation_id}`),
                undefined,
                false,
              );
              if (d) setHistorical(d);
            }}
          >
            查看固定历史解释
          </button>
        </article>
      ))}
      {historical && (
        <article>
          <h3>固定历史解释</h3>
          <p>
            当次结果：
            {(historical.result.risk || historical.result.rules?.status === "risk_excluded")
              ? "风险排除"
              : (historical.result.rules?.passes ?? historical.result.passes) === true
                ? "满足条件"
                : (historical.result.rules?.passes ?? historical.result.passes) === false
                  ? "未满足条件"
                  : "待评估"}
            ；应用状态 {historical.application}。
          </p>
          <Diagnostic value={historical} />
        </article>
      )}
    </>
  );
}
export function ZoneScatter({ rows, sweet, edge }: { rows: any[]; sweet: number; edge: number }) {
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
