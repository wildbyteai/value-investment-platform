// 左侧两级导航：服务器下发的每个菜单（config/menus-v1.json）是一个分组，分组下缩进列出它的页面。
// 点页面即切换；当前页面高亮（aria-current="page"）；分组可折叠，折叠状态记在本机（vip-nav-collapsed），
// 当前页面所在的分组总是展开。只有一个可见页面的菜单直接显示成一项。
// 宽屏可收起成 64px 图标栏（vip-nav-mini，点分组图标进入该组当前/第一个页面）；窄屏（<900px）时导航收成抽屉。
import React, { useEffect, useState } from "react";

export type NavMenu = { key: string; label: string; icon: string; tabs: { key: string; label: string }[] };

const STORE = "vip-nav-collapsed";
const MINI = "vip-nav-mini";
const NARROW = "(max-width: 900px)";
function readCollapsed(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(STORE) || "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function SideNav({
  menus, active, busy, unread, open, onClose, onNavigate, foot,
}: {
  menus: NavMenu[];
  active: string;
  busy: boolean;
  unread: number;
  open: boolean;
  onClose: () => void;
  onNavigate: (key: string) => void;
  foot: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState<string[]>(readCollapsed);
  const [miniPref, setMiniPref] = useState(() => { try { return localStorage.getItem(MINI) === "1"; } catch { return false; } });
  const [narrow, setNarrow] = useState(() => typeof matchMedia === "function" && matchMedia(NARROW).matches);
  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const mq = matchMedia(NARROW);
    const on = () => setNarrow(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  useEffect(() => { try { localStorage.setItem(MINI, miniPref ? "1" : "0"); } catch {} }, [miniPref]);
  const mini = miniPref && !narrow;
  const activeMenu = menus.find((m) => m.tabs.some((t) => t.key === active))?.key;
  useEffect(() => {
    try { localStorage.setItem(STORE, JSON.stringify(collapsed)); } catch {}
  }, [collapsed]);
  // 切到某个页面时，它所在的分组自动展开（并记住展开）。
  useEffect(() => {
    if (activeMenu && collapsed.includes(activeMenu)) setCollapsed((c) => c.filter((k) => k !== activeMenu));
  }, [activeMenu]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  const toggle = (k: string) =>
    setCollapsed((c) => (c.includes(k) ? c.filter((x) => x !== k) : [...c, k]));
  const badge = (n: number) => (n ? <span className="unread" aria-label={`${n} 条未读`}>{n}</span> : null);
  return (
    <>
      {open && <div className="nav-scrim" aria-hidden="true" onClick={onClose} />}
      <nav id="side-nav" aria-label="业务导航" className={"sidebar" + (open ? " open" : "") + (mini ? " mini" : "")}>
        <div className="brand">
          {mini ? <span>价</span> : <>价投<span>宝</span></>}
          <button className="text small nav-close" aria-label="收起导航菜单" onClick={onClose}>✕</button>
        </div>
        <div className="nav-groups">
          {menus.map((m) => {
            const isMonitor = m.key === "monitor";
            if (m.tabs.length === 1) {
              const t = m.tabs[0];
              return (
                <div key={m.key} className="nav-group" data-menu={m.key}>
                  <button
                    className="nav-item nav-single"
                    disabled={busy}
                    aria-current={active === t.key ? "page" : undefined}
                    title={m.label + " / " + t.label}
                    onClick={() => onNavigate(t.key)}
                  >
                    <span className="nav-icon" aria-hidden="true">{m.icon}</span>
                    <span className="nav-label">{m.label}</span>
                    {isMonitor && badge(unread)}
                  </button>
                </div>
              );
            }
            const shut = collapsed.includes(m.key) && activeMenu !== m.key;
            return (
              <div key={m.key} className="nav-group" data-menu={m.key}>
                <button
                  className={"nav-head" + (activeMenu === m.key ? " has-active" : "")}
                  aria-expanded={mini ? undefined : !shut}
                  aria-controls={mini ? undefined : "nav-" + m.key}
                  aria-current={mini && activeMenu === m.key ? "page" : undefined}
                  title={mini ? m.label : undefined}
                  disabled={mini && busy}
                  onClick={() => (mini ? onNavigate(activeMenu === m.key ? active : m.tabs[0].key) : toggle(m.key))}
                >
                  <span className="nav-icon" aria-hidden="true">{m.icon}</span>
                  <span className="nav-label">{m.label}</span>
                  {isMonitor && (shut || mini) && badge(unread)}
                  <span className="nav-caret" aria-hidden="true">{shut ? "▸" : "▾"}</span>
                </button>
                <ul id={"nav-" + m.key} className="nav-sub" hidden={shut}>
                  {m.tabs.map((t) => (
                    <li key={t.key}>
                      <button
                        className="nav-item"
                        disabled={busy}
                        aria-current={active === t.key ? "page" : undefined}
                        onClick={() => onNavigate(t.key)}
                      >
                        <span className="nav-label">{t.label}</span>
                        {isMonitor && t.key === "inbox" && badge(unread)}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
        {foot}
        <div className="nav-mini-toggle">
          <button
            className="nav-mini-toggle-btn"
            aria-label={mini ? "展开导航栏" : "收起导航栏"}
            title={mini ? "展开导航栏" : "收起导航栏"}
            onClick={() => setMiniPref(!miniPref)}
          >
            {mini ? "»" : "« 收起"}
          </button>
        </div>
      </nav>
    </>
  );
}
