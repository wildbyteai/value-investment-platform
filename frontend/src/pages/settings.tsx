// 后台设置：数据源、资讯源、采集定时器、Skill、模型配置、告警发送。
import React, { useEffect, useRef, useState } from "react";
import { api, post, session, ApiError, authHeaders } from "../core/client";
import { Ctx, ZONE, pct, num, signed, time, any, useLoad, Failed, ZoneBadge, Check, short, tone, Kpi } from "../components/common";
import { Diagnostic, GapList, FinancialSummary, ResearchResult, ReferenceQuality, ReferenceValuation, CompareRuns, Dialog, dimensionName, criterionName, human, when } from "../components/ui";
export function Sources(_: Ctx) {
  const list = useLoad<any[]>("/api/admin/sources");
  const layer: Record<string, string> = { news: "资讯", companies: "公司", strategy: "策略" };
  return (
    <>
      <Failed error={list.error} />
      <table>
        <thead><tr><th>数据源</th><th>喂给</th><th>内容</th><th>触发</th><th>市场</th><th>需要密钥</th></tr></thead>
        <tbody>
          {list.value?.map((s) => (
            <tr key={s.key}><td>{s.name}<div className="muted">{s.key}</div></td><td>{layer[s.layer] || s.layer}</td><td>{s.kind}</td>
              <td>{{ manual_script: "手动脚本", scheduled: "定时任务", upload: "上传" }[s.trigger as string] || s.trigger}</td>
              <td>{s.markets.join("、") || "—"}</td><td>{s.secret_env || "—"}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

async function upload(files: FileList) {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  form.append("score", "true");
  const r = await fetch("/api/news/import", { method: "POST", body: form, headers: authHeaders(), credentials: "same-origin" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, typeof data.detail === "string" ? data.detail : "上传未完成");
  return data;
}
export function Feeds({ allow, busy, execute }: Ctx) {
  const feeds = useLoad<any[]>("/api/news/feeds");
  const [files, setFiles] = useState<FileList | null>(null);
  const [rss, setRss] = useState({ feed_key: "", name: "", url: "", schedule: "daily 08:30" });
  const canWrite = any(allow, "source.manage", "analysis.override");
  const canAdmin = any(allow, "source.manage", "system.configure");
  return (
    <>
      {canWrite && (
        <section>
          <h3>上传每日资讯 Excel</h3>
          <p className="muted">可一次选多个文件；按文件名识别资讯源（如“创新药每日动态_2026-09-30.xlsx”）。重复内容自动跳过，同一件事合并为一个事件。</p>
          <input type="file" accept=".xlsx" multiple onChange={(e) => setFiles(e.target.files)} />
          <button disabled={busy || !files?.length} onClick={async () => (await execute(() => upload(files!), (r: any) => `导入完成：新增 ${r.files.reduce((s: number, f: any) => s + f.new_items, 0)} 条，重复 ${r.files.reduce((s: number, f: any) => s + f.duplicate_items, 0)} 条；${r.scoring ? `打分 ${r.scoring.events} 个事件` : ""}${r.scoring?.error ? `（${r.scoring.error}，已用规则匹配）` : ""}。`, false)) !== undefined && feeds.reload()}>
            导入并打分
          </button>
        </section>
      )}
      <h3>资讯源</h3>
      <Failed error={feeds.error} />
      <table>
        <thead><tr><th>名称</th><th>类型</th><th>最近一次</th><th>状态</th>{canWrite && <th></th>}</tr></thead>
        <tbody>
          {feeds.value?.map((f) => (
            <tr key={f.id}><td>{f.name}{f.url && <div className="muted">{f.url}</div>}</td><td>{f.kind === "rss" ? `RSS${f.schedule ? ` · ${f.schedule}` : ""}` : "Excel 上传"}</td>
              <td>{time(f.last_run_at)}</td><td>{f.last_status || "—"}</td>
              {canWrite && <td>{f.kind === "rss" && <button className="quiet" disabled={busy} onClick={async () => (await execute(() => post(`/api/news/feeds/${f.id}/run`, {}), (r: any) => `抓取完成：新增 ${r.new_items} 条。`, false)) !== undefined && feeds.reload()}>立即抓取</button>}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      {canAdmin && (
        <form className="form" onSubmit={async (e) => { e.preventDefault(); (await execute(() => post("/api/admin/news-feeds", { ...rss, kind: "rss" }), "已登记 RSS 源。", false)) !== undefined && feeds.reload(); }}>
          <h4>登记 RSS / Atom 源</h4>
          <label>标识<input required value={rss.feed_key} onChange={(e) => setRss({ ...rss, feed_key: e.target.value })} placeholder="cls-telegraph" /></label>
          <label>名称<input required value={rss.name} onChange={(e) => setRss({ ...rss, name: e.target.value })} /></label>
          <label>地址<input required type="url" value={rss.url} onChange={(e) => setRss({ ...rss, url: e.target.value })} /></label>
          <label>计划<input value={rss.schedule} onChange={(e) => setRss({ ...rss, schedule: e.target.value })} /></label>
          <button disabled={busy}>登记</button>
          <p className="muted">定时抓取由服务器 cron 执行 python -m app.jobs news。</p>
        </form>
      )}
    </>
  );
}
export const PRESETS = [
  { provider_key: "deepseek", name: "DeepSeek", base_url: "https://api.deepseek.com", model: "deepseek-chat", api_key_env: "VIP_DEEPSEEK_API_KEY", search_mode: "none" },
  { provider_key: "qwen", name: "通义千问", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", api_key_env: "VIP_QWEN_API_KEY", search_mode: "qwen_enable_search" },
  { provider_key: "zhipu", name: "智谱 GLM", base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-air", api_key_env: "VIP_ZHIPU_API_KEY", search_mode: "zhipu_web_search" },
  { provider_key: "kimi", name: "Kimi", base_url: "https://api.moonshot.cn/v1", model: "kimi-k3", api_key_env: "VIP_MOONSHOT_API_KEY", search_mode: "kimi_search" },
  { provider_key: "openai", name: "OpenAI", base_url: "https://api.openai.com/v1", model: "gpt-6-luna", api_key_env: "VIP_OPENAI_API_KEY", search_mode: "openai_web_search" },
];
export const SEARCH_LABEL: Record<string, string> = { none: "不联网", qwen_enable_search: "通义 · 内置联网", zhipu_web_search: "智谱 · web_search", kimi_search: "Kimi · 官方搜索", openai_web_search: "OpenAI · web_search" };
export function Models({ busy, execute }: Ctx) {
  const list = useLoad<any>("/api/admin/llm-providers");
  const blank = { ...PRESETS[0], is_default: true, enabled: true, temperature: 0 };
  const [form, setForm] = useState<any>(blank);
  const [editing, setEditing] = useState<string | null>(null);
  const v = list.value;
  async function save(e: any) {
    e.preventDefault();
    const r = await execute(() => (editing ? api(`/api/admin/llm-providers/${editing}`, { method: "PUT", body: JSON.stringify(form) }) : post("/api/admin/llm-providers", form)), "模型配置已保存。", false);
    if (r !== undefined) { setEditing(null); setForm(blank); list.reload(); }
  }
  return (
    <>
      <p className="intro">资讯关联打分使用 OpenAI 兼容接口的大模型，默认 DeepSeek。这里只登记“密钥放在哪个环境变量”，密钥本身由服务器环境注入，不进数据库。</p>
      <Failed error={list.error} />
      {v && (
        <>
          <p>当前使用：<strong>{v.active || `${v.builtin_default.name}（内置默认）`}</strong>{!v.providers.length && !v.builtin_default.key_configured && <span className="notice"> 服务器尚未设置 {v.builtin_default.api_key_env}，资讯关联暂用规则匹配。</span>}</p>
          <table>
            <thead><tr><th>模型</th><th>地址</th><th>密钥变量</th><th>联网</th><th>状态</th><th></th></tr></thead>
            <tbody>
              {v.providers.map((p: any) => (
                <tr key={p.id}><td>{p.name}<div className="muted">{p.model}</div></td><td>{p.base_url}</td><td>{p.api_key_env} {p.key_configured ? "✓ 已设置" : "✗ 未设置"}</td>
                  <td>{SEARCH_LABEL[p.search_mode] || p.search_mode}</td>
                  <td>{p.enabled ? (p.is_default ? "默认" : "可用") : "停用"}</td>
                  <td><button className="quiet" onClick={() => { setEditing(p.id); setForm({ ...p, temperature: p.options?.temperature ?? 0 }); }}>编辑</button></td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <form className="form" onSubmit={save}>
        <h4>{editing ? "编辑模型" : "添加模型"}</h4>
        {!editing && <label>预设<select onChange={(e) => setForm({ ...form, ...PRESETS[Number(e.target.value)] })}>{PRESETS.map((p, i) => <option key={p.provider_key} value={i}>{p.name}</option>)}</select></label>}
        {["provider_key", "name", "base_url", "model", "api_key_env"].map((k) => (
          <label key={k}>{{ provider_key: "标识", name: "名称", base_url: "接口地址", model: "模型名", api_key_env: "密钥环境变量" }[k]}<input required value={form[k] || ""} disabled={k === "provider_key" && !!editing} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></label>
        ))}
        <label>联网方式<select value={form.search_mode || "none"} onChange={(e) => setForm({ ...form, search_mode: e.target.value })}>
          {Object.entries((v?.search_modes as Record<string, string>) || SEARCH_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select></label>
        <p className="muted">采集定时器只能选能联网的模型。联网用的是厂商自带的搜索，和对话共用同一个密钥，不需要另配搜索服务。</p>
        <label>温度<input type="number" min={0} max={2} step={0.1} value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} /></label>
        <label className="inline"><input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /> 设为默认</label>
        <label className="inline"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> 启用</label>
        <button disabled={busy}>保存</button>
        {editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setForm(blank); }}>取消</button>}
      </form>
    </>
  );
}

// ------------------------------------------------------------------ 采集定时器 / Skill
export const WEEK = ["一", "二", "三", "四", "五", "六", "日"];
export const RUN_STATUS: Record<string, string> = { running: "执行中", succeeded: "成功", failed: "失败" };
export function Collectors({ busy, execute }: Ctx) {
  const list = useLoad<any[]>("/api/admin/collectors");
  const opts = useLoad<any>("/api/admin/collectors/options");
  const blank = { name: "", prompt: "", provider_id: "", skill_id: "", enabled: true, kind: "daily", times: "08:30", weekdays: [1, 2, 3, 4, 5, 6, 7], minutes: 240 };
  const [form, setForm] = useState<any>(blank);
  const [editing, setEditing] = useState<string | null>(null);
  const [runsOf, setRunsOf] = useState<string | null>(null);
  const runs = useLoad<any[]>(runsOf ? `/api/admin/collectors/${runsOf}/runs` : "/api/admin/collectors", [runsOf]);
  const searchable = (opts.value?.providers || []).filter((p: any) => p.search_mode !== "none");
  const body = () => ({
    name: form.name, prompt: form.prompt, provider_id: form.provider_id || searchable[0]?.id, skill_id: form.skill_id || null, enabled: form.enabled,
    schedule: form.kind === "daily" ? { type: "daily", times: String(form.times).split(/[,，\s]+/).filter(Boolean), weekdays: form.weekdays } : { type: "interval", minutes: Number(form.minutes) },
  });
  async function save(e: any) {
    e.preventDefault();
    const r = await execute(() => (editing ? api(`/api/admin/collectors/${editing}`, { method: "PUT", body: JSON.stringify(body()) }) : post("/api/admin/collectors", body())), "采集定时器已保存。", false);
    if (r !== undefined) { setEditing(null); setForm(blank); list.reload(); }
  }
  function edit(t: any) {
    setEditing(t.id);
    setForm({ name: t.name, prompt: t.prompt, provider_id: t.provider_id || "", skill_id: t.skill_id || "", enabled: t.enabled, kind: t.schedule.type,
      times: (t.schedule.times || ["08:30"]).join(", "), weekdays: t.schedule.weekdays || [1, 2, 3, 4, 5, 6, 7], minutes: t.schedule.minutes || 240 });
  }
  return (
    <>
      <p className="intro">像 Agent 定时任务一样采集资讯：写好提示词、选一个能联网的模型（可再选一个 Skill 让模型按流程走），到点自动执行。采到的资讯进入资讯雷达，和 Excel、RSS 一样去重、关联公司、等你确认。时间按北京时间。</p>
      <Failed error={list.error || opts.error} />
      {opts.value && !searchable.length && <p className="notice">还没有能联网的模型。先到 模型配置 添加通义、智谱、Kimi 或 OpenAI，并选择联网方式。</p>}
      <table>
        <thead><tr><th>定时器</th><th>模型 / Skill</th><th>周期</th><th>下次执行</th><th>最近一次</th><th></th></tr></thead>
        <tbody>
          {list.value?.map((t) => (
            <tr key={t.id}>
              <td>{t.name}<div className="muted">{t.prompt.slice(0, 60)}{t.prompt.length > 60 ? "…" : ""}</div></td>
              <td>{t.provider || "—"}<div className="muted">{t.skill ? `Skill：${t.skill}` : "不用 Skill"}</div></td>
              <td>{t.enabled ? t.schedule_text : "已停用"}</td>
              <td>{t.enabled ? time(t.next_run_at) : "—"}</td>
              <td>{t.last_status || "尚未执行"}<div className="muted">{t.last_run_at ? time(t.last_run_at) : ""}</div></td>
              <td className="actions">
                <button className="quiet" disabled={busy} onClick={async () => { const r = await execute(() => post(`/api/admin/collectors/${t.id}/run`, {}), (x: any) => (x.status === "succeeded" ? `采集完成：采到 ${x.items_found} 条，新增 ${x.stats.new_items} 条。` : `采集失败：${x.error}`), false); if (r !== undefined) { list.reload(); runs.reload(); } }}>立即执行</button>
                <button className="quiet" onClick={() => edit(t)}>编辑</button>
                <button className="quiet" onClick={() => setRunsOf(runsOf === t.id ? null : t.id)}>{runsOf === t.id ? "收起记录" : "执行记录"}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {runsOf && (
        <section>
          <h4>执行记录</h4>
          <table>
            <thead><tr><th>开始</th><th>触发</th><th>结果</th><th>模型 / Skill</th><th>说明</th></tr></thead>
            <tbody>
              {(runs.value || []).map((r: any) => (
                <tr key={r.id}><td>{time(r.started_at)}</td><td>{r.trigger === "manual" ? "手动" : "定时"}</td>
                  <td>{RUN_STATUS[r.status] || r.status}{r.status === "succeeded" && ` · ${r.items_found} 条`}</td>
                  <td>{r.model || "—"}<div className="muted">{r.skill_key ? `${r.skill_key} v${r.skill_version}` : ""}</div></td>
                  <td>{r.error || (r.stats?.searches?.length ? `搜索：${r.stats.searches.join("；")}` : r.stats?.new_items != null ? `新增 ${r.stats.new_items}，重复 ${r.stats.duplicate_items}` : "—")}
                    {r.output_excerpt && <details><summary>模型原始输出</summary><pre>{r.output_excerpt}</pre></details>}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <form className="form" onSubmit={save}>
        <h4>{editing ? "编辑采集定时器" : "新建采集定时器"}</h4>
        <label>名称<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="创新药重点公司早报" /></label>
        <label>提示词<textarea required value={form.prompt} onChange={(e) => setForm({ ...form, prompt: e.target.value })} placeholder="采集过去 24 小时内诺诚健华、百济神州、信达生物的公告、临床进展和重要新闻……" /></label>
        <label>模型<select required value={form.provider_id || searchable[0]?.id || ""} onChange={(e) => setForm({ ...form, provider_id: e.target.value })}>
          {searchable.map((p: any) => <option key={p.id} value={p.id}>{p.name} · {p.model}（{p.search_label}）{p.key_configured ? "" : " · 密钥未设置"}</option>)}
        </select></label>
        <label>Skill（可选）<select value={form.skill_id} onChange={(e) => setForm({ ...form, skill_id: e.target.value })}>
          <option value="">不用 Skill</option>
          {(opts.value?.skills || []).map((s: any) => <option key={s.id} value={s.id}>{s.name}{s.enabled ? "" : "（已停用）"}</option>)}
        </select></label>
        <label>周期<select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}><option value="daily">每天定时</option><option value="interval">固定间隔</option></select></label>
        {form.kind === "daily" ? (
          <>
            <label>执行时间（可多个，逗号分隔）<input value={form.times} onChange={(e) => setForm({ ...form, times: e.target.value })} placeholder="08:30, 17:00" /></label>
            <div className="chips">{WEEK.map((w, i) => (
              <label key={w} className="inline"><input type="checkbox" checked={form.weekdays.includes(i + 1)} onChange={(e) => setForm({ ...form, weekdays: e.target.checked ? [...form.weekdays, i + 1].sort() : form.weekdays.filter((d: number) => d !== i + 1) })} /> 周{w}</label>
            ))}</div>
          </>
        ) : (
          <label>间隔分钟（不少于 {opts.value?.min_interval_minutes ?? 60}）<input type="number" min={opts.value?.min_interval_minutes ?? 60} step={30} value={form.minutes} onChange={(e) => setForm({ ...form, minutes: e.target.value })} /></label>
        )}
        <label className="inline"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> 启用</label>
        <button disabled={busy || !searchable.length}>保存</button>
        {editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setForm(blank); }}>取消</button>}
        <p className="muted">定时执行需要服务器每 5 分钟跑一次 python -m app.jobs collect。</p>
      </form>
    </>
  );
}
export function Skills({ busy, execute }: Ctx) {
  const list = useLoad<any[]>("/api/admin/skills");
  const blank = { skill_key: "", name: "", description: "", body: "", enabled: true };
  const [form, setForm] = useState<any>(blank);
  const [editing, setEditing] = useState<string | null>(null);
  async function save(e: any) {
    e.preventDefault();
    const r = await execute(() => (editing ? api(`/api/admin/skills/${editing}`, { method: "PUT", body: JSON.stringify(form) }) : post("/api/admin/skills", form)), "Skill 已保存。", false);
    if (r !== undefined) { setEditing(null); setForm(blank); list.reload(); }
  }
  return (
    <>
      <p className="intro">Skill 是一段可复用的执行流程（按步骤写清楚先查什么、怎么筛、怎么判断）。采集定时器选了 Skill，模型就按它的流程执行。修改步骤会升版本，执行记录里能看到用的是哪一版。</p>
      <Failed error={list.error} />
      <table>
        <thead><tr><th>Skill</th><th>说明</th><th>版本</th><th>被引用</th><th>状态</th><th></th></tr></thead>
        <tbody>
          {list.value?.map((s) => (
            <tr key={s.id}><td>{s.name}<div className="muted">{s.skill_key}</div></td><td>{s.description || "—"}</td><td>v{s.version}</td>
              <td>{s.used_by} 个定时器</td><td>{s.enabled ? "启用" : "停用"}</td>
              <td className="actions"><button className="quiet" onClick={() => { setEditing(s.id); setForm({ skill_key: s.skill_key, name: s.name, description: s.description, body: s.body, enabled: s.enabled }); }}>编辑</button>
                <button className="quiet" disabled={busy || s.used_by > 0} title={s.used_by ? "还有定时器在用" : ""} onClick={async () => { if (!confirm(`删除 Skill「${s.name}」？`)) return; (await execute(() => api(`/api/admin/skills/${s.id}`, { method: "DELETE" }), "Skill 已删除。", false)) !== undefined && list.reload(); }}>删除</button></td></tr>
          ))}
        </tbody>
      </table>
      <form className="form" onSubmit={save}>
        <h4>{editing ? "编辑 Skill" : "新建 Skill"}</h4>
        <label>标识（小写字母、数字、-）<input required pattern="[a-z0-9_\-]+" value={form.skill_key} onChange={(e) => setForm({ ...form, skill_key: e.target.value })} placeholder="pharma-daily" /></label>
        <label>名称<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="创新药公司日报流程" /></label>
        <label>说明<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
        <label>执行流程（Markdown）<textarea required rows={12} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder={"1. 逐个公司检索过去 24 小时的交易所公告\n2. 再检索临床试验、医保谈判、BD 授权新闻\n3. 只保留可能影响长期价值的事件，删掉股价异动类快讯\n4. 每条写清楚涉及的公司和代码"} /></label>
        <label className="inline"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> 启用</label>
        <button disabled={busy}>保存</button>
        {editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setForm(blank); }}>取消</button>}
      </form>
    </>
  );
}
export function NotifyAdmin(_: Ctx) {
  const s = useLoad<any>("/api/admin/notify");
  const v = s.value;
  return (
    <>
      <Failed error={s.error} />
      {v && (
        <>
          <p>发件人：<strong>{v.sender_name} &lt;{v.sender}&gt;</strong></p>
          <p>SMTP：{v.smtp_configured ? `${v.smtp_host}:${v.smtp_port}${v.smtp_starttls ? "（STARTTLS）" : "（TLS）"}` : "未配置（只发站内通知；设置 VIP_SMTP_HOST 等环境变量后启用邮件）"}</p>
          <p>邮件投递：{Object.entries(v.email_counts).map(([k, n]) => `${k} ${n}`).join("，") || "暂无"}</p>
          <h4>收件人（角色：{v.recipient_roles.join("、")}）</h4>
          <table>
            <thead><tr><th>人员</th><th>邮箱</th><th>邮件</th></tr></thead>
            <tbody>{v.recipients.map((r: any) => <tr key={r.login}><td>{r.name}</td><td>{r.email || "未填写"}</td><td>{r.email_enabled ? "开" : "关"}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </>
  );
}
// 后台任务：接入记录与处理任务（只显示运维元数据）。
export function TasksPage({ data, allow, busy, execute }: any) {
  return (
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
  );
}
