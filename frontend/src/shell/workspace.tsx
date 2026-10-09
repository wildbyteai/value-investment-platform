// 工作台外壳：左侧菜单与顶部页签（由服务器按角色下发），页面数据读取，统一的忙碌/错误/提示状态。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError } from "../core/client";
import { Diagnostic, when } from "../components/ui";
import { ThemeToggle } from "./account";
import { PAGES, SELF_LOADING } from "../pages";
import { useUnread } from "../pages/monitor";

type Menu = { key: string; label: string; icon: string; tabs: { key: string; label: string }[] };

export function Workspace({ identity, identityPanel }: any) {
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
      const visible = (user.menus || []).flatMap((m: any) => m.tabs.map((t: any) => t.key));
      if (!visible.includes(target)) target = visible[0] || "";
      if (!target) throw new Error("当前账号在这个工作区没有可用的菜单，请联系管理员分配角色。");
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
  const unread = useUnread([tab, message]);
  const ctx = { allow, busy, execute };
  const menus: Menu[] = me?.menus || [];
  const current = menus.find((m) => m.tabs.some((t) => t.key === tab)) || menus[0];
  const labelOf = (k: string) => menus.flatMap((m) => m.tabs).find((t) => t.key === k)?.label || "";
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
      <nav aria-label="业务导航" className="sidebar">
        <div className="brand">价投<span>宝</span></div>
        {menus.map((m) => (
          <button
            key={m.key}
            className="nav-item"
            disabled={busy}
            aria-current={current?.key === m.key ? "page" : undefined}
            onClick={() => navigate(m.tabs[0].key)}
          >
            <span className="nav-icon" aria-hidden="true">{m.icon}</span>
            {m.label}
            {m.key === "monitor" && !!unread && <span className="unread">{unread}</span>}
          </button>
        ))}
        <div className="nav-foot">
          <strong>{me?.user?.display_name}</strong>
          <p className="muted">
            {(me?.roles || []).map((r: any) => r.label).join("、")}
          </p>
          {identityPanel}
        </div>
      </nav>
      <div className="main-col">
        <div className="topbar">
          <div className="crumb">{reader ? "固定原文" : current?.label}</div>
          <div className="subtabs" role="tablist" aria-label={current?.label}>
            {current?.tabs.map((t) => (
              <button key={t.key} role="tab" aria-selected={tab === t.key} disabled={busy} onClick={() => navigate(t.key)}>
                {t.label}
              </button>
            ))}
          </div>
          <div className="top-actions">
            <button className="quiet small" disabled={busy} onClick={() => load().catch(() => {})}>
              刷新
            </button>
            <ThemeToggle />
          </div>
        </div>
      <main>
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
              返回{labelOf(returnTo?.tab || tab)}
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
          {data && PAGES[tab]?.({
            data, busy, allow, execute, read, error, selected, setSelected, watchIds, toggle, navigate, runKey,
            nextKey: () => setRunKey(crypto.randomUUID()),
            openCompany: (id: string) => { setSelected(id); navigate("companies"); },
          })}
          {!data && !busy && !error && <p>尚未读取当前页面，点击刷新重试。</p>}
        </div>
      </main>
      <footer>本地研究预览 · 真实资料 · A/H独立估值 · 不产生交易指令</footer>
      </div>
    </div>
  );
}
