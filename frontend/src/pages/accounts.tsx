// 后台设置：账号与角色、审计日志。角色是固定的五种，权限说明来自服务器。
import React, { useState } from "react";
import { post, send } from "../core/client";
import { Ctx, Failed, time, useLoad } from "../components/common";

type Role = { key: string; label: string; description: string; permissions: string[] };
type User = {
  id: string;
  login: string;
  display_name: string;
  disabled: boolean;
  has_password: boolean;
  roles: string[];
  role_labels: string[];
  active_sessions: number;
  last_seen_at: string | null;
};
type Page<T> = { items: T[]; total: number; limit: number; offset: number };

const PAGE = 20;

function RolePicker({ roles, value, onChange }: { roles: Role[]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="chips" role="group" aria-label="角色">
      {roles.map((r) => (
        <label key={r.key} className="check" title={r.description}>
          <input
            type="checkbox"
            checked={value.includes(r.key)}
            onChange={(e) => onChange(e.target.checked ? [...value, r.key] : value.filter((k) => k !== r.key))}
          />
          {r.label}
        </label>
      ))}
    </div>
  );
}

function Pager({ page, offset, setOffset }: { page: Page<any> | null; offset: number; setOffset: (n: number) => void }) {
  if (!page || page.total <= page.limit) return null;
  const last = Math.max(0, Math.floor((page.total - 1) / page.limit) * page.limit);
  return (
    <div className="pager">
      <button className="quiet small" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - page.limit))}>上一页</button>
      <span className="muted">
        第 {offset / page.limit + 1} / {last / page.limit + 1} 页 · 共 {page.total} 条
      </span>
      <button className="quiet small" disabled={offset >= last} onClick={() => setOffset(offset + page.limit)}>下一页</button>
    </div>
  );
}

export function Users({ allow, busy, execute }: Ctx) {
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const users = useLoad<Page<User>>(`/api/admin/users?limit=${PAGE}&offset=${offset}${search ? `&q=${encodeURIComponent(search)}` : ""}`);
  const catalog = useLoad<{ roles: Role[]; permissions: { key: string; label: string }[] }>("/api/admin/roles");
  const roles = catalog.value?.roles || [];
  const [draft, setDraft] = useState({ login: "", display_name: "", roles: ["viewer"] as string[] });
  const [editing, setEditing] = useState<{ id: string; roles: string[]; name: string } | null>(null);
  const [secret, setSecret] = useState<{ login: string; password: string } | null>(null);
  const canManage = allow("user.manage");
  const canAssign = allow("role.assign");

  async function act(fn: () => Promise<any>, ok: string | ((r: any) => string)) {
    const r = await execute(fn, ok, false);
    if (r !== undefined) users.reload();
    return r;
  }

  return (
    <>
      <p className="intro">账号属于当前工作区。新账号会得到一次性初始密码，请当面或用安全渠道交给本人，登录后让对方自己修改。</p>
      {secret && (
        <p className="notice" role="status">
          {secret.login} 的一次性密码：<code>{secret.password}</code>（只显示这一次）
          <button className="quiet small" onClick={() => setSecret(null)}>我已记下</button>
        </p>
      )}
      <section className="panel">
        <div className="panel-head">
          <h3>账号</h3>
          <form className="right" onSubmit={(e) => { e.preventDefault(); setOffset(0); setSearch(q.trim()); }}>
            <input aria-label="搜索账号" placeholder="搜索登录名或姓名" value={q} onChange={(e) => setQ(e.target.value)} />
          </form>
        </div>
        <Failed error={users.error || catalog.error} />
        <div className="table-scroll">
          <table>
            <thead>
              <tr><th>姓名</th><th>登录名</th><th>角色</th><th>状态</th><th>最近活动</th>{(canManage || canAssign) && <th></th>}</tr>
            </thead>
            <tbody>
              {users.value?.items.map((u) =>
                editing?.id === u.id ? (
                  <tr key={u.id}>
                    <td>{canManage ? <input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /> : u.display_name}</td>
                    <td>{u.login}</td>
                    <td colSpan={3}>{canAssign ? <RolePicker roles={roles} value={editing.roles} onChange={(v) => setEditing({ ...editing, roles: v })} /> : u.role_labels.join("、")}</td>
                    <td className="actions">
                      <button
                        className="small"
                        disabled={busy || !editing.roles.length}
                        onClick={async () => {
                          if (canManage && editing.name.trim() && editing.name !== u.display_name)
                            if ((await act(() => send(`/api/admin/users/${u.id}`, "PATCH", { display_name: editing.name }), "已保存。")) === undefined) return;
                          if (canAssign && editing.roles.slice().sort().join() !== u.roles.join())
                            if ((await act(() => send(`/api/admin/users/${u.id}/roles`, "PUT", { roles: editing.roles }), "角色已更新，下次刷新页面即生效。")) === undefined) return;
                          setEditing(null);
                        }}
                      >
                        保存
                      </button>
                      <button className="quiet small" onClick={() => setEditing(null)}>取消</button>
                    </td>
                  </tr>
                ) : (
                  <tr key={u.id} className={u.disabled ? "muted" : ""}>
                    <td>{u.display_name}</td>
                    <td>{u.login}</td>
                    <td>{u.role_labels.map((l) => <span key={l} className="chip">{l}</span>)}</td>
                    <td>{u.disabled ? <span className="badge">已停用</span> : u.has_password ? "正常" : <span className="badge">未设密码</span>}</td>
                    <td>{u.last_seen_at ? time(u.last_seen_at) : "—"}{u.active_sessions ? ` · ${u.active_sessions} 处登录` : ""}</td>
                    {(canManage || canAssign) && (
                      <td className="actions">
                        <button className="quiet small" disabled={busy} onClick={() => setEditing({ id: u.id, roles: u.roles, name: u.display_name })}>编辑</button>
                        {canManage && (
                          <>
                            <button
                              className="quiet small"
                              disabled={busy}
                              onClick={async () => {
                                if (!confirm(`给 ${u.display_name} 生成新的一次性密码？对方所有已登录的浏览器会退出。`)) return;
                                const r = await act(() => post(`/api/admin/users/${u.id}/password`, {}), "已重置密码。");
                                if (r?.initial_password) setSecret({ login: u.login, password: r.initial_password });
                              }}
                            >
                              重置密码
                            </button>
                            {!!u.active_sessions && (
                              <button className="quiet small" disabled={busy} onClick={() => act(() => post(`/api/admin/users/${u.id}/sign-out`, {}), "已让该账号在所有浏览器退出。")}>
                                强制退出
                              </button>
                            )}
                            <button
                              className="quiet small"
                              disabled={busy}
                              onClick={() => {
                                if (!u.disabled && !confirm(`停用 ${u.display_name}？对方将无法登录。`)) return;
                                act(() => send(`/api/admin/users/${u.id}`, "PATCH", { disabled: !u.disabled }), u.disabled ? "已启用。" : "已停用，并退出了所有浏览器。");
                              }}
                            >
                              {u.disabled ? "启用" : "停用"}
                            </button>
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
        {users.value && !users.value.items.length && <p className="panel-body muted">没有匹配的账号。</p>}
        <Pager page={users.value} offset={offset} setOffset={setOffset} />
      </section>

      {canManage && (
        <form
          className="form panel panel-body"
          onSubmit={async (e) => {
            e.preventDefault();
            const r = await act(() => post("/api/admin/users", draft), (r: any) => `已开通 ${r.display_name}。`);
            if (r) {
              if (r.initial_password) setSecret({ login: r.login, password: r.initial_password });
              setDraft({ login: "", display_name: "", roles: ["viewer"] });
            }
          }}
        >
          <h4>开通账号</h4>
          <label>登录名（一般用邮箱）<input required autoComplete="off" value={draft.login} onChange={(e) => setDraft({ ...draft, login: e.target.value })} /></label>
          <label>姓名<input required value={draft.display_name} onChange={(e) => setDraft({ ...draft, display_name: e.target.value })} /></label>
          <RolePicker roles={roles} value={draft.roles} onChange={(v) => setDraft({ ...draft, roles: v })} />
          <button disabled={busy || !draft.roles.length}>开通并生成初始密码</button>
        </form>
      )}

      <section className="panel">
        <div className="panel-head"><h3>角色说明</h3><span className="right">角色固定为五种；一个人可以同时有多个角色，权限取并集</span></div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>角色</th><th>适合谁</th><th>能做什么</th></tr></thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.key}>
                  <td><strong>{r.label}</strong></td>
                  <td>{r.description}</td>
                  <td>{r.permissions.map((p) => <span key={p} className="chip">{catalog.value?.permissions.find((x) => x.key === p)?.label || p}</span>)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

const ACTION_LABEL: [string, string][] = [
  ["identity.", "账号"],
  ["auth.", "登录"],
  ["admin.", "后台设置"],
  ["news.", "资讯"],
  ["strategy.", "策略"],
  ["judgment", "研判"],
];

export function Audit(_: Ctx) {
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState("");
  const log = useLoad<Page<any>>(`/api/admin/audit?limit=${PAGE * 2}&offset=${offset}${action ? `&action=${encodeURIComponent(action)}` : ""}`);
  return (
    <>
      <div className="toolbar">
        <p className="intro">谁在什么时候做了什么。只读，不能修改或删除。</p>
        <label>
          类别
          <select value={action} onChange={(e) => { setOffset(0); setAction(e.target.value); }}>
            <option value="">全部</option>
            {ACTION_LABEL.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
      </div>
      <Failed error={log.error} />
      <section className="panel">
        <div className="table-scroll">
          <table>
            <thead><tr><th>时间</th><th>操作人</th><th>动作</th><th>对象</th><th>详情</th></tr></thead>
            <tbody>
              {log.value?.items.map((a) => (
                <tr key={a.id}>
                  <td>{time(a.at)}</td>
                  <td>{a.actor ? a.actor.display_name : "系统"}</td>
                  <td><code>{a.action}</code></td>
                  <td>{a.entity_type}</td>
                  <td className="muted">{Object.keys(a.detail || {}).length ? JSON.stringify(a.detail).slice(0, 160) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {log.value && !log.value.items.length && <p className="panel-body muted">暂无记录。</p>}
        <Pager page={log.value} offset={offset} setOffset={setOffset} />
      </section>
    </>
  );
}
