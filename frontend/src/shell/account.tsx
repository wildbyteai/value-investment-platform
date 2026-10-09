// 登录页、账号与工作区面板、白天/黑夜切换。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
export function LoginForm({ onDone }: { onDone: (r: any) => void }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(await post("/api/auth/login", { login, password }));
    } catch (err) {
      setError((err as Error).message);
      setPassword("");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <form className="panel login-card" onSubmit={submit}>
        <h1>价投宝</h1>
        <p className="muted">请用管理员为你开通的账号登录。</p>
        {error && <p role="alert" className="notice danger">{error}</p>}
        <label>
          账号
          <input autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} required autoFocus />
        </label>
        <label>
          密码
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" disabled={busy || !login || !password}>{busy ? "登录中…" : "登录"}</button>
      </form>
    </main>
  );
}
export function AccountPanel({ workspaces, workspace, setWorkspace }: any) {
  const [pw, setPw] = useState({ current: "", next: "" });
  const [note, setNote] = useState("");
  async function logout() {
    await post("/api/auth/logout", {}).catch(() => {});
    location.reload();
  }
  async function change(e: React.FormEvent) {
    e.preventDefault();
    try {
      await post("/api/auth/password", { current: pw.current, new: pw.next });
      setNote("密码已修改，其他浏览器已退出登录。");
      setPw({ current: "", next: "" });
    } catch (err) {
      setNote((err as Error).message);
    }
  }
  return (
    <details className="identity">
      <summary>账号与工作区</summary>
      {workspaces.length > 1 && (
        <label>
          工作区
          <select value={workspace} onChange={(e) => setWorkspace(e.target.value)}>
            {workspaces.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
        </label>
      )}
      <form onSubmit={change}>
        <label>当前密码<input type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></label>
        <label>新密码（至少 12 位）<input type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} /></label>
        <button type="submit" className="quiet" disabled={!pw.current || !pw.next}>修改密码</button>
      </form>
      {note && <p className="muted">{note}</p>}
      <button className="quiet" onClick={logout}>退出登录</button>
    </details>
  );
}
// 白天 / 黑夜模式：手动切换，记在本机浏览器。
export function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("vip-theme", theme); } catch {}
  }, [theme]);
  const dark = theme === "dark";
  return (
    <button className="quiet small theme-toggle" aria-label={dark ? "切换到白天模式" : "切换到黑夜模式"} title={dark ? "白天模式" : "黑夜模式"} onClick={() => setTheme(dark ? "light" : "dark")}>
      {dark ? "☀ 白天" : "☾ 黑夜"}
    </button>
  );
}
