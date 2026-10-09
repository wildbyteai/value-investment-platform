// 入口：判断登录方式（正式账号 / 本机开发身份），再进入工作台。
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, session } from "./core/client";
import { AccountPanel, LoginForm } from "./shell/account";
import { Workspace } from "./shell/workspace";
import "./shell/style.css";

export function App() {
  const [mode, setMode] = useState<"" | "dev" | "session">("");
  const [account, setAccount] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/api/auth/state")
      .then((st) => {
        session.mode = st.mode;
        if (st.user) setAccount(st);
        setMode(st.mode);
      })
      .catch((e) => setError(e.message));
  }, []);
  if (error) return <p role="alert" className="notice danger">{error}</p>;
  if (mode === "dev") return <DevApp />;
  if (mode !== "session") return null;
  if (!account) return <LoginForm onDone={setAccount} />;
  return <SessionApp account={account} />;
}
export function SessionApp({ account }: any) {
  const workspaces = account.workspaces || [];
  const [workspace, setWorkspace] = useState(workspaces[0]?.id || "");
  if (!workspaces.length) return <p role="alert" className="notice danger">这个账号还没有加入任何工作区，请联系管理员。</p>;
  const panel = <AccountPanel workspaces={workspaces} workspace={workspace} setWorkspace={setWorkspace} />;
  return <Workspace key={workspace} identity={{ login: account.user.login, workspace }} identityPanel={panel} />;
}
export function DevApp() {
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
  const identityPanel = (
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
  );
  return (
    <>
      {error && <p role="alert" className="notice danger">{error}</p>}
      {active && (
        <Workspace key={active.login + active.workspace} identity={active} identityPanel={identityPanel} />
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
