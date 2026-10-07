import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, post, session, ApiError } from "./client";
import {
  Diagnostic,
  GapList,
  FinancialSummary,
  ResearchResult,
  ReferenceQuality,
  ReferenceValuation,
  CompareRuns,
  dimensionName,
  criterionName,
  human,
  when,
} from "./ui";
import { AuthorJudgment, Judgment } from "./judgments";
import { TemplateEditor } from "./template";
import {
  NewsRadar,
  StrikeZone,
  CompanyMainline,
  Inbox,
  AlertsList,
  NotifySettings,
  Sources,
  Feeds,
  Models,
  NotifyAdmin,
  useUnread,
} from "./mainline";
import "./style.css";
// 四个业务菜单 + 后台设置。每个菜单下的分页签复用原有研究页面。
type Section = { key: string; label: string; tabs: [string, string][] };
const sections: Section[] = [
  { key: "radar", label: "资讯雷达", tabs: [["events", "事件与关联"], ["news", "原始资料与研判"]] },
  { key: "company", label: "公司档案", tabs: [["companies", "公司"], ["today", "今日概览"], ["research", "研究快照"], ["mine", "我的自选与笔记"]] },
  { key: "strategy", label: "策略（击球区）", tabs: [["zone", "击球区"], ["strategy", "策略规则"]] },
  { key: "monitor", label: "监控告警", tabs: [["inbox", "我的通知"], ["alerts", "全部告警"], ["notify-settings", "通知设置"]] },
  { key: "settings", label: "后台设置", tabs: [["sources", "数据源"], ["feeds", "资讯源与导入"], ["models", "模型配置"], ["notify", "告警发送"], ["tasks", "后台任务"]] },
];
const labels: Record<string, string> = Object.fromEntries(sections.flatMap((s) => s.tabs.map(([k, l]) => [k, l])));
const sectionOf = (tab: string) => sections.find((s) => s.tabs.some(([k]) => k === tab)) || sections[0];
// Tabs whose views load their own data (mainline.tsx).
const SELF_LOADING = new Set(["events", "zone", "inbox", "alerts", "notify-settings", "sources", "feeds", "models", "notify"]);
const tabPermission: Record<string, string[]> = {
  tasks: ["ops.read"],
  mine: ["watchlist.own"],
  sources: ["source.manage", "system.configure"],
  feeds: ["source.manage", "analysis.override", "system.configure"],
  models: ["model.configure"],
  notify: ["system.configure"],
};
const companyTabs = [
  "经营质量与待补依据",
  "财务与估值依据",
  "资料与研判",
  "评分规则",
];
function App() {
  const [ids, setIds] = useState<any>();
  const [error, setError] = useState("");
  const [login, setLogin] = useState("research@demo");
  const [workspace, setWorkspace] = useState("");
  const [active, setActive] = useState<any>();
  useEffect(() => {
    api("/api/identities")
      .then((value) => {
        setIds(value);
        const ws =
          value.workspaces.find((w: any) => w.has_real_data) ||
          value.workspaces[0];
        setWorkspace(ws.id);
        setActive({ login, workspace: ws.id });
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <header>
        <div>
          <h1>价值投资研究</h1>
          <p>查看公司、依据与下一步</p>
        </div>
        <details className="identity">
          <summary>本地开发身份与工作区</summary>
          <p className="muted">仅供本机开发验证，尚未接入正式登录。</p>
          <label>
            身份
            <select value={login} onChange={(e) => setLogin(e.target.value)}>
              {ids?.users.map((u: any) => (
                <option key={u.login} value={u.login}>
                  {u.display_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            工作区
            <select
              value={workspace}
              onChange={(e) => setWorkspace(e.target.value)}
            >
              {ids?.workspaces.map((w: any) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={() => setActive({ login, workspace })}
            disabled={!workspace}
          >
            切换身份与工作区
          </button>
        </details>
      </header>
      {error && <p role="alert">{error}</p>}
      {active && (
        <Workspace key={active.login + active.workspace} identity={active} />
      )}
      <footer>本地研究预览 · 真实资料 · A/H独立估值 · 不产生交易指令</footer>
    </>
  );
}
function Workspace({ identity }: any) {
  const [me, setMe] = useState<any>();
  const [tab, setTab] = useState("events");
  const [state, setState] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [more, setMore] = useState(false);
  const [selected, setSelected] = useState("");
  const [reader, setReader] = useState<any>();
  const [returnTo, setReturnTo] = useState<any>();
  const [runKey, setRunKey] = useState(crypto.randomUUID());
  const scope = useRef(0),
    live = useRef(true),
    route = useRef("events");
  const gate = useRef(false);
  const allow = (p: string) => me?.permissions?.includes(p);
  const data = state?.route === tab ? state.value : null;
  useEffect(() => {
    session.login = identity.login;
    session.workspace = identity.workspace;
    live.current = true;
    load("events").catch(() => {});
    return () => {
      live.current = false;
      scope.current++;
    };
  }, []);
  async function fetchPage(target: string, user: any) {
    if (SELF_LOADING.has(target)) return {};
    if (["today", "companies"].includes(target)) {
      const cs = await api("/api/companies");
      const companyResults = await Promise.allSettled(
        cs.map(async (c: any) => ({
          ...c,
          score: await api(`/api/companies/${c.id}/score`),
          timeline: await api(`/api/companies/${c.id}/timeline`),
          catalog: await api(`/api/judgments/catalog/${c.id}`),
        })),
      );
      const companies = companyResults
        .filter((r: any) => r.status === "fulfilled")
        .map((r: any) => r.value);
      const failures = companyResults.flatMap((r: any, i: number) =>
        r.status === "rejected" ? [`${cs[i].name}：${r.reason.message}`] : [],
      );
      if (cs.length && !companies.length) throw new Error(failures.join("；"));
      let watch = null;
      if (user.permissions.includes("watchlist.own")) {
        try {
          watch = await api("/api/me/watchlist");
        } catch (e) {
          failures.push("自选状态未读到，请刷新重试。");
        }
      }
      return {
        companies,
        failures,
        judgments: await api("/api/judgments"),
        watch,
        runs: await api("/api/research/runs"),
      };
    }
    if (target === "news")
      return {
        items: await api("/api/intake/items"),
        judgments: await api("/api/judgments"),
        companies: await api("/api/companies"),
      };
    if (target === "research") {
      const runs = await api("/api/research/runs");
      return {
        runs,
        detail: runs.length
          ? await api(`/api/research/runs/${runs[0].id}`)
          : null,
      };
    }
    if (target === "strategy")
      return {
        rule: await api("/api/strategy/current"),
        changes: await api("/api/strategy/transitions"),
        seals: await api("/api/strategy/seals"),
      };
    if (target === "mine") {
      const cs = await api("/api/companies");
      return {
        watch: await api("/api/me/watchlist"),
        notes: await api("/api/me/notes"),
        companies: await Promise.all(
          cs.map(async (c: any) => ({
            ...c,
            score: await api(`/api/companies/${c.id}/score`),
          })),
        ),
      };
    }
    if (target === "tasks")
      return {
        sources: await api("/api/worker/sources"),
        tasks: await api("/api/worker/tasks"),
      };
  }
  async function load(target = route.current) {
    const token = ++scope.current;
    setBusy(true);
    setError("");
    try {
      const user = await api("/api/me");
      if (!live.current || token !== scope.current) return;
      setMe(user);
      if (!user.permissions.includes("research.read") && !(tabPermission[target] || []).some((p) => user.permissions.includes(p)))
        target = "tasks";
      const value = await fetchPage(target, user);
      if (!live.current || token !== scope.current) return;
      route.current = target;
      setTab(target);
      setState({ route: target, value });
      return value;
    } catch (e) {
      if (live.current && token === scope.current)
        setError((e as Error).message);
      throw e;
    } finally {
      if (live.current && token === scope.current) setBusy(false);
    }
  }
  async function execute(
    fn: () => Promise<any>,
    success?: string | ((r: any) => string),
    reload = true,
  ) {
    if (gate.current) return;
    gate.current = true;
    const token = scope.current;
    setBusy(true);
    setError("");
    setMessage("");
    let result: any;
    try {
      result = await fn();
      if (!live.current || token !== scope.current) return;
      if (success)
        setMessage(typeof success === "function" ? success(result) : success);
      if (reload) {
        try {
          await load();
        } catch (e) {
          if (live.current)
            setError(
              "操作已保存，但页面回读失败：" +
                (e as Error).message +
                "。请刷新核对结果。",
            );
        }
      }
      return result;
    } catch (e) {
      if (live.current && token === scope.current) {
        const err = e as ApiError;
        setError(
          (err.status === 403 ? "当前身份无权操作：" : "") +
            err.message +
            "。输入已保留。",
        );
      }
      return undefined;
    } finally {
      gate.current = false;
      if (live.current) setBusy(false);
    }
  }
  async function navigate(t: string) {
    if (busy) return;
    setMessage("");
    setReader(null);
    setReturnTo(null);
    setTab(t);
    route.current = t;
    setMore(false);
    try {
      await load(t);
    } catch {}
  }
  async function read(id: string, revision?: string) {
    const doc = await execute(
      () =>
        api(
          `/api/intake/items/${id}${revision ? `?revision_id=${revision}` : ""}`,
        ),
      undefined,
      false,
    );
    if (doc) {
      setReturnTo({ tab, selected });
      setReader(doc);
    }
  }
  const canSee = (k: string) => (tabPermission[k] ? tabPermission[k].some((p) => allow(p)) : allow("research.read"));
  const unread = useUnread([tab, message]);
  const ctx = { allow, busy, execute };
  const watchIds = data?.watch
    ? new Set(data.watch.map((w: any) => w.security_id))
    : null;
  async function toggle(s: any) {
    await execute(
      () =>
        api(`/api/me/watchlist/${s.security_id}`, {
          method: watchIds?.has(s.security_id) ? "DELETE" : "POST",
        }),
      watchIds?.has(s.security_id)
        ? "已移出对应证券自选。"
        : "已加入对应证券自选。",
    );
  }
  return (
    <div className="shell">
      <nav aria-label="业务导航">
        {sections
          .filter((sec) => sec.tabs.some(([k]) => canSee(k)))
          .map((sec) => (
            <button
              key={sec.key}
              disabled={busy}
              aria-current={sectionOf(tab).key === sec.key ? "page" : undefined}
              onClick={() => navigate(sec.tabs.find(([k]) => canSee(k))![0])}
            >
              {sec.label}
              {sec.key === "monitor" && !!unread && <span className="unread">{unread}</span>}
            </button>
          ))}
        <p className="muted">
          {me?.user?.display_name}
          <br />
          {allow("research.read")
            ? "已保存资料可阅读；评分依据不足时显示待评估。"
            : "查看当前工作区的运维记录。"}
        </p>
      </nav>
      <main>
        <div className="subtabs" role="tablist" aria-label={sectionOf(tab).label}>
          {sectionOf(tab)
            .tabs.filter(([k]) => canSee(k))
            .map(([k, l]) => (
              <button key={k} role="tab" className={tab === k ? "" : "quiet"} aria-selected={tab === k} disabled={busy} onClick={() => navigate(k)}>
                {l}
              </button>
            ))}
        </div>
        <div className="toolbar">
          <h2>{reader ? "固定原文" : `${sectionOf(tab).label} · ${labels[tab]}`}</h2>
          <button
            className="quiet"
            disabled={busy}
            onClick={() => load().catch(() => {})}
          >
            刷新当前页
          </button>
        </div>
        {busy && <p role="status">正在读取或保存…</p>}
        {error && (
          <p className="notice danger" role="alert">
            {error}
          </p>
        )}
        {!!data?.failures?.length && (
          <p className="notice" role="status">
            部分读取未完成：{data.failures.join("；")}
            。其余资料可继续阅读，刷新可重试。
          </p>
        )}
        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}
        {reader && (
          <article>
            <button
              className="quiet"
              onClick={() => {
                setReader(null);
                if (returnTo) {
                  setTab(returnTo.tab);
                  setSelected(returnTo.selected);
                }
              }}
            >
              返回{labels[returnTo?.tab || tab]}
            </button>
            <h3>{reader.title}</h3>
            <p className="muted">
              {reader.source.name}；资料日期 {reader.publication.date || "未知"}
              ；系统取得 {when(reader.observed_at)}
            </p>
            {reader.metadata_state === "unavailable" && (
              <p className="notice">
                此旧修订未保存标题、摘要、日期与网址；不使用当前元数据替代。
              </p>
            )}
            {reader.summary_text && <p>{reader.summary_text}</p>}
            {reader.original_text ? (
              <div className="body-text">{reader.original_text}</div>
            ) : (
              <p>原文尚未取得，现有摘要仍可阅读。</p>
            )}
            <p className="muted">
              许可：{reader.reading_metadata.license || "见来源政策"}；
              {reader.reading_metadata.change_notice}
            </p>
            {reader.body_access.url && (
              <a href={reader.body_access.url} target="_blank" rel="noreferrer">
                来源入口
              </a>
            )}
            {reader.reading_metadata.history_url && (
              <a
                href={reader.reading_metadata.history_url}
                target="_blank"
                rel="noreferrer"
              >
                作者与历史
              </a>
            )}
            <Diagnostic
              value={{
                revision: reader.revision,
                source: reader.source,
                metadata: reader.reading_metadata,
              }}
            />
          </article>
        )}
        <div hidden={!!reader}>
          {data && tab === "today" && (
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
                    <button
                      disabled={busy}
                      onClick={() => {
                        setSelected(c.id);
                        navigate("companies");
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
                    className="quiet"
                    onClick={() => navigate("research")}
                  >
                    查看快照
                  </button>
                </p>
              ) : (
                <p>尚无研究快照；阅读并研判后可生成预览。</p>
              )}
            </>
          )}
          {data && tab === "companies" && (
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
          )}
          {data && tab === "news" && (
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
                    className="quiet"
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
              <button className="quiet" onClick={() => navigate("companies")}>
                到公司页核对评价项并补充研判
              </button>
            </>
          )}
          {data && tab === "research" && (
            <ResearchPage
              data={data}
              busy={busy}
              read={read}
              execute={execute}
              allow={allow}
              runKey={runKey}
              nextKey={() => setRunKey(crypto.randomUUID())}
            />
          )}
          {data && tab === "strategy" && (
            <StrategyPage
              data={data}
              allow={allow}
              busy={busy}
              execute={execute}
            />
          )}
          {data && tab === "mine" && (
            <Mine
              data={data}
              busy={busy}
              execute={execute}
              openCompany={(id: string) => {
                setSelected(id);
                navigate("companies");
              }}
            />
          )}
          {data && tab === "events" && <NewsRadar {...ctx} />}
          {data && tab === "zone" && <StrikeZone {...ctx} />}
          {data && tab === "inbox" && <Inbox {...ctx} />}
          {data && tab === "alerts" && <AlertsList {...ctx} />}
          {data && tab === "notify-settings" && <NotifySettings {...ctx} />}
          {data && tab === "sources" && <Sources {...ctx} />}
          {data && tab === "feeds" && <Feeds {...ctx} />}
          {data && tab === "models" && <Models {...ctx} />}
          {data && tab === "notify" && <NotifyAdmin {...ctx} />}
          {data && tab === "tasks" && (
            <>
              <p>当前工作区的接入记录与本地处理任务。这里只显示运维元数据。</p>
              <h3>接入记录</h3>
              {data.sources.length ? (
                data.sources.map((r: any) => (
                  <article key={r.id}>
                    <h4>{r.source_key}</h4>
                    <p>{r.status}</p>
                  </article>
                ))
              ) : (
                <p>暂无接入记录。</p>
              )}
              <h3>处理任务</h3>
              {data.tasks.length ? (
                data.tasks.map((r: any) => (
                  <article key={r.id}>
                    <p>
                      {r.stage}：
                      {r.status === "completed"
                        ? "完成"
                        : r.status === "failed"
                          ? "失败待恢复"
                          : "等待处理"}
                    </p>
                    <p>{r.error}</p>
                    {r.status === "failed" && allow("job.retry") && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          execute(
                            () => post(`/api/worker/outbox/${r.id}/retry`, {}),
                            "已仅重试此项任务。",
                          )
                        }
                      >
                        只重试此项任务
                      </button>
                    )}
                  </article>
                ))
              ) : (
                <p>当前有界列表暂无任务；不代表没有重要业务动态。</p>
              )}
            </>
          )}
          {!data && !busy && !error && <p>尚未读取当前页面，点击刷新重试。</p>}
        </div>
      </main>
    </div>
  );
}
function CompanyPanel({
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
          <button disabled={busy || !c.catalog.length} onClick={startAuthor}>
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
                  className="quiet"
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
            <button className="quiet" onClick={research}>
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
                  className="quiet"
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
              <button
                disabled={busy || !c.catalog.length}
                onClick={startAuthor}
              >
                补充真实研判
              </button>
            )}
            <button className="quiet" onClick={research}>
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
function ResearchPage({
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
        <button
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
            className="quiet"
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
const fieldName = (k: string) =>
  ({
    "company.quality_score": "经营质量分",
    "company.coverage": "加权覆盖度",
    "security.valuation_score": "证券估值分",
    "metrics.roe_ttm": "TTM ROE",
    "metrics.cfo_profit_3y": "三年累计CFO/利润",
    "metrics.net_debt_ebitda": "净负债/EBITDA",
  })[k] || k;
function StrategyPage({ data, allow, busy, execute }: any) {
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
function Mine({ data, busy, execute, openCompany }: any) {
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
                        className="quiet"
                        onClick={() => openCompany(w.company_id)}
                      >
                        查看公司与参考报价
                      </button>
                      <button
                        className="quiet"
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
        <button
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
createRoot(document.getElementById("root")!).render(<App />);
