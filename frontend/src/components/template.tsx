import React, { useState } from "react";
import { api, post } from "../core/client";
import { Diagnostic, dimensionName } from "./ui";
export function TemplateEditor({ company, template, allow, execute }: any) {
  const [draft, setDraft] = useState("[]");
  const [preview, setPreview] = useState<any>();
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);
  let patches: any[] = [];
  try {
    const parsed = JSON.parse(draft);
    if (!Array.isArray(parsed)) throw Error();
    patches = parsed;
  } catch {}
  const valid = (() => {
    try {
      return Array.isArray(JSON.parse(draft));
    } catch {
      return false;
    }
  })();
  function change(d: string, field: string, value: any) {
    if (!valid) {
      setError("先修正高级配置的JSON，再使用表单，输入会保留。");
      return;
    }
    const next = JSON.parse(draft),
      index = next.findIndex((p: any) => p.dimension === d),
      p = index >= 0 ? next[index] : { dimension: d };
    delete p.disabled;
    if (field === "enabled") {
      p.event_policy = value
        ? {
            enabled: true,
            half_life_days:
              p.event_policy?.half_life_days ||
              template.dimension_policies[d].event_policy.half_life_days ||
              template.event_contribution.half_life_calendar_days[d] ||
              90,
          }
        : { enabled: false };
    } else p[field] = value;
    if (index >= 0) next[index] = p;
    else next.push(p);
    setDraft(JSON.stringify(next, null, 2));
    setPreview(null);
    setConfirm(false);
    setError("");
  }
  const weights = Object.fromEntries(
    Object.entries(template.weights).map(([d, w]: any) => [
      d,
      patches.find((p) => p.dimension === d)?.weight ?? w,
    ]),
  );
  const total = Object.values(weights).reduce(
    (a: number, w: any) => a + Number(w),
    0,
  ) as number;
  async function simulate() {
    if (!valid) {
      setError("高级配置必须是JSON数组；请修正输入。");
      return;
    }
    const r = await execute(async () => {
      const current = await api(`/api/templates/${company.id}`);
      return {
        ...(await post(`/api/templates/${company.id}/preview`, {
          patches: JSON.parse(draft),
        })),
        version: current.version,
        patches: JSON.parse(draft),
      };
    });
    if (r) {
      setPreview(r);
      setConfirm(false);
    }
  }
  async function publish() {
    const r = await execute(
      () =>
        post(`/api/templates/${company.id}/publish`, {
          expected_version: preview.version,
          patches: preview.patches,
        }),
      "模板新版本已发布。已有研究快照保留原口径；策略绑定仍需重新模拟并发布。",
    );
    if (r) {
      setPreview(null);
      setConfirm(false);
      setDraft("[]");
    }
  }
  return (
    <>
      <p>
        已发布父链：{template.levels_applied.join(" → ")}
        。未修改字段继续继承；政策修改整份替换。
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>维度</th>
              <th>权重 / 草稿</th>
              <th>事件贡献</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(template.weights).map(([d, w]: any) => (
              <tr key={d}>
                <th>{dimensionName(d)}</th>
                <td>
                  {allow("template.edit") ? (
                    <input
                      aria-label={`${dimensionName(d)}权重`}
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={weights[d]}
                      onChange={(e) => change(d, "weight", e.target.value)}
                    />
                  ) : (
                    `${Number(w) * 100}%`
                  )}
                </td>
                <td>
                  {allow("template.edit") ? (
                    <label className="radio">
                      <input
                        type="checkbox"
                        checked={
                          patches.find((p) => p.dimension === d)?.event_policy
                            ?.enabled ??
                          template.dimension_policies[d]?.event_policy
                            ?.enabled ??
                          true
                        }
                        onChange={(e) => change(d, "enabled", e.target.checked)}
                      />
                      接受事件
                    </label>
                  ) : template.dimension_policies[d]?.event_policy?.enabled ? (
                    "接受事件"
                  ) : (
                    "仅基准"
                  )}
                </td>
                <td>
                  {template.field_origins?.[d]?.weight || template.origins[d]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {allow("template.edit") && (
        <>
          <p className={Math.abs(total - 1) > 1e-10 ? "notice" : ""}>
            当前表单权重合计 {(total * 100).toFixed(2)}
            %，必须为100%；不自动调整其他权重。高级禁用/新增仍由服务端校验。
          </p>
          <details>
            <summary>高级配置（完整政策与注册维度）</summary>
            <label>
              模板差异 JSON
              <textarea
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setPreview(null);
                  setConfirm(false);
                  setError("");
                }}
              />
            </label>
            <p>表单与高级配置共用一份草稿；非法输入不会被表单覆盖。</p>
          </details>
          {error && (
            <p role="alert" className="danger">
              {error}
            </p>
          )}
          <button disabled={!valid} onClick={simulate}>
            预览模板差异
          </button>
          {preview && (
            <section>
              <h4>预览：已发布 → 草稿</h4>
              {Object.entries(preview.resolved.weights).map(([d, w]: any) => (
                <p key={d}>
                  {dimensionName(d)}：{Number(template.weights[d] || 0) * 100}%
                  → {Number(w) * 100}%；
                  {preview.resolved.dimension_policies[d]?.event_policy?.enabled
                    ? "接受事件"
                    : "仅基准"}
                </p>
              ))}
              <p>这是配置差异，不是虚构的评分变化；完整政策在诊断中核对。</p>
              <Diagnostic value={preview.resolved} />
              {allow("template.publish") &&
                (confirm ? (
                  <>
                    <p className="notice">
                      确认发布这份已预览的配置？现有快照与策略版本保持原输入。
                    </p>
                    <button onClick={publish}>确认发布模板</button>
                    <button className="quiet" onClick={() => setConfirm(false)}>
                      取消
                    </button>
                  </>
                ) : (
                  <button onClick={() => setConfirm(true)}>
                    发布模板新版本
                  </button>
                ))}
            </section>
          )}
        </>
      )}
      <Diagnostic value={template} />
    </>
  );
}
