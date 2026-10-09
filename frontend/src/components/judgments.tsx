import React, { useState } from "react";
import { post } from "../core/client";
import { Dialog, Diagnostic, dimensionName, criterionName } from "./ui";
const dateInput = (d: Date) => d.toLocaleDateString("sv-SE");
export function AuthorJudgment({
  company,
  catalog,
  documents,
  execute,
  close,
  error,
}: any) {
  const [dim, setDim] = useState(catalog[0]?.dimension || "");
  const [criterion, setCriterion] = useState("");
  const [grade, setGrade] = useState("");
  const [reason, setReason] = useState("");
  const [confidence, setConfidence] = useState("0.8");
  const [from, setFrom] = useState(dateInput(new Date()));
  const [to, setTo] = useState(dateInput(new Date(Date.now() + 89 * 86400000)));
  const [effectiveFrom, setEffectiveFrom] = useState(dateInput(new Date()));
  const [validUntil, setValidUntil] = useState(
    dateInput(new Date(Date.now() + 89 * 86400000)),
  );
  const [docId, setDocId] = useState(documents[0]?.id || "");
  const [quote, setQuote] = useState("");
  const [key, setKey] = useState(crypto.randomUUID());
  const [localError, setLocalError] = useState("");
  const [saving, setSaving] = useState(false);
  const rubric = catalog.find((r: any) => r.dimension === dim),
    item = rubric?.criteria.find((c: any) => c.key === criterion),
    doc = documents.find((d: any) => d.id === docId),
    start = doc?.original_text?.indexOf(quote) ?? -1;
  const changed = () => {
    setKey(crypto.randomUUID());
    setLocalError("");
  };
  async function save() {
    if (!grade || !criterion || !reason.trim() || !quote.trim() || start < 0) {
      setLocalError("请选择档位、评价项并填写理由；证据片段须与原文完全一致。");
      return;
    }
    setSaving(true);
    const r = await execute(
      () =>
        post(
          "/api/judgments",
          {
            company_id: company.id,
            dimension: dim,
            rubric_ref: rubric.rubric_ref,
            criterion,
            grade: Number(grade),
            reason,
            confidence,
            period_start: from,
            period_end: to,
            effective_from: new Date(
              effectiveFrom + "T00:00:00+08:00",
            ).toISOString(),
            valid_until: new Date(validUntil + "T23:59:59+08:00").toISOString(),
            evidence: [
              {
                source_revision_id: doc.revision.id,
                hash: doc.revision.hash,
                start: Array.from(doc.original_text.slice(0, start)).length,
                end:
                  Array.from(doc.original_text.slice(0, start)).length +
                  Array.from(quote).length,
                quote,
                relation: "supports",
              },
            ],
          },
          { "Idempotency-Key": key },
        ),
      (r: any) =>
        r.applicability === "eligible"
          ? "研判已保存，本项依据可用于当前评分；完整分数仍需满足其他评价项。已有快照保持原结果。"
          : "研判已保存，但期间或证据类别不满足当前评分要求；请核对公司页。已有快照保持原结果。",
    );
    setSaving(false);
    if (r) close();
  }
  return (
    <Dialog
      title={`补充真实研判 · ${company.name}`}
      close={() => {
        if (!saving) close();
      }}
    >
      <p>档位表示证据支持的评价，未调查不等于0档。当前只创建单项定性研判。</p>
      <label>
        评价维度
        <select
          value={dim}
          onChange={(e) => {
            setDim(e.target.value);
            setCriterion("");
            setGrade("");
            changed();
          }}
        >
          {catalog.map((r: any) => (
            <option key={r.dimension} value={r.dimension}>
              {dimensionName(r.dimension)}
            </option>
          ))}
        </select>
      </label>
      <label>
        评价项
        <select
          value={criterion}
          onChange={(e) => {
            setCriterion(e.target.value);
            setGrade("");
            changed();
          }}
        >
          <option value="">请选择评价项</option>
          {rubric?.criteria.map((c: any) => (
            <option key={c.key} value={c.key}>
              {criterionName(c.key)}
            </option>
          ))}
        </select>
      </label>
      <fieldset>
        <legend>证据支持的档位</legend>
        {item?.anchors.map((a: string, i: number) => (
          <label className="radio" key={i}>
            <input
              type="radio"
              name="grade"
              value={i}
              checked={grade === String(i)}
              onChange={() => {
                setGrade(String(i));
                changed();
              }}
            />
            {i}档：{a}
          </label>
        )) || <p>先选择评价项，再显示对应锚点。</p>}
      </fieldset>
      <div className="form-grid">
        <label>
          研究期间开始
          <input
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              changed();
            }}
          />
        </label>
        <label>
          研究期间结束
          <input
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              changed();
            }}
          />
        </label>
      </div>
      <div className="form-grid">
        <label>
          判断有效开始
          <input
            type="date"
            value={effectiveFrom}
            onChange={(e) => {
              setEffectiveFrom(e.target.value);
              changed();
            }}
          />
        </label>
        <label>
          判断有效截止
          <input
            type="date"
            value={validUntil}
            onChange={(e) => {
              setValidUntil(e.target.value);
              changed();
            }}
          />
        </label>
      </div>
      <p className="muted">
        有效期限受模板限制（最多 {rubric?.validity_days}{" "}
        天）；与当前研究时点不匹配的期间不进入当前评分。
      </p>
      <label>
        固定来源修订
        <select
          value={docId}
          onChange={(e) => {
            setDocId(e.target.value);
            setQuote("");
            changed();
          }}
        >
          {documents.map((d: any) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
        </select>
      </label>
      {doc && (
        <details>
          <summary>展开固定原文，复制支持片段</summary>
          <p className="body-text">{doc.original_text}</p>
        </details>
      )}
      <label>
        支持证据片段
        <textarea
          value={quote}
          onChange={(e) => {
            setQuote(e.target.value);
            changed();
          }}
          placeholder="从上述原文复制可核对的完整片段"
        />
      </label>
      {quote && (
        <p className={start < 0 ? "danger" : "muted"}>
          {start < 0
            ? "片段未在固定原文中找到，请核对标点与换行。"
            : "已定位到固定原文；服务端将再次校验。"}
        </p>
      )}
      <label>
        研判理由
        <textarea
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            changed();
          }}
          placeholder="哪些事实支持这一档？有什么局限？"
        />
      </label>
      <label>
        研判置信度（不是影响强度）
        <input
          type="number"
          min="0"
          max="1"
          step="0.01"
          value={confidence}
          onChange={(e) => {
            setConfidence(e.target.value);
            changed();
          }}
        />
      </label>
      {(localError || error) && (
        <p role="alert" className="danger">
          {localError || error}
        </p>
      )}
      <button
        disabled={
          saving ||
          grade === "" ||
          !quote.trim() ||
          !reason.trim() ||
          !criterion
        }
        onClick={save}
      >
        {saving ? "正在保存" : "保存研判"}
      </button>
    </Dialog>
  );
}
export function Judgment({ j, catalog = [], execute, editable }: any) {
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [key, setKey] = useState(crypto.randomUUID());
  const [releaseKey] = useState(crypto.randomUUID());
  const [localError, setLocalError] = useState("");
  const [saving, setSaving] = useState(false);
  const identity = j.effective || j.identity;
  const criterion = catalog
    .find((c: any) => c.rubric_ref === identity.rubric_ref)
    ?.criteria.find((c: any) => c.key === identity.criterion);
  async function save(release = false) {
    if (!release && (value === "" || !reason.trim())) {
      setLocalError("请选择新值并填写理由，未选择不能保存。");
      return;
    }
    setSaving(true);
    const r = await execute(
      () =>
        post(
          `/api/judgments/${j.slot_key}/override`,
          {
            value: release
              ? {}
              : j.kind === "rubric"
                ? { ...identity, grade: Number(value), reason }
                : { ...j.effective, magnitude: value, reason },
            release,
          },
          {
            "If-Match-Generation": String(j.generation),
            "Idempotency-Key": release ? releaseKey : key,
          },
        ),
      release
        ? "人工覆盖已解除，当前判断等待重评；旧AUTO不会自动恢复。"
        : "研判修订已保存。当前公司评分按新判断核对，历史快照保持原结果。",
    );
    setSaving(false);
    if (r) {
      setValue("");
      setReason("");
      setKey(crypto.randomUUID());
    }
  }
  return (
    <section className="judgment">
      <h4>
        {dimensionName(j.dimension)} ·{" "}
        {criterionName(identity.criterion) || "事件影响"}
      </h4>
      <p>
        {j.effective
          ? `当前有效值：${j.kind === "rubric" ? j.effective.grade : j.effective.magnitude}`
          : j.proposal ? "AI研判建议 · 待确认，尚未计入评分" : "当前等待重评，无有效判断"}
      </p>
      {identity.period_start && (
        <p className="muted">
          研究期间 {identity.period_start} 至 {identity.period_end}
        </p>
      )}
      {j.effective?.reason && <p>理由：{j.effective.reason}</p>}
      {j.proposal && <>
        <p>建议 {j.proposal.grade} 档：{criterion?.anchors?.[j.proposal.grade]}</p>
        <p>依据与判断：{j.proposal.reason}</p>
        <p className="muted">局限与反证：{j.proposal.limitations}</p>
        <p className="muted">{j.proposal.author_label} · 固定原文研究；尚无置信度校准结果。</p>
      </>}
      {j.evidence?.map((e: any, i: number) => <details key={i}><summary>{e.relation === "contradicts" ? "阅读反证或限制条件" : "阅读支持证据"}</summary><blockquote>{e.quote}</blockquote></details>)}
      <Diagnostic value={j} />
      {editable && (
        <details>
          <summary>{j.proposal ? "确认或修改研判建议" : "修改 / 解除人工覆盖"}</summary>
          <label>
            {j.kind === "rubric"
              ? "选择新档位"
              : "新影响（−1到1；零为无净影响）"}
            {j.kind === "rubric" ? (
              <select
                value={value}
                onChange={(e) => {
                  setValue(e.target.value);
                  setKey(crypto.randomUUID());
                }}
              >
                <option value="">未选择</option>
                {(
                  criterion?.anchors || [
                    "最低档",
                    "较低档",
                    "中间档",
                    "较高档",
                    "最高档",
                  ]
                ).map((a: string, i: number) => (
                  <option key={i} value={i}>
                    {i}档：{a}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="number"
                min="-1"
                max="1"
                step="any"
                value={value}
                onChange={(e) => {
                  setValue(e.target.value);
                  setKey(crypto.randomUUID());
                }}
              />
            )}
          </label>
          <label>
            修改理由
            <textarea
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                setKey(crypto.randomUUID());
              }}
            />
          </label>
          {localError && <p role="alert">{localError}</p>}
          <button
            disabled={saving || value === "" || !reason.trim()}
            onClick={() => save()}
          >
            {j.proposal ? "确认并保存研判" : "保存人工覆盖"}
          </button>
          {j.author_type === "human" && (
            <button
              disabled={saving}
              className="quiet"
              onClick={() => save(true)}
            >
              解除人工覆盖
            </button>
          )}
          <p className="muted">解除后等待新的合法重评，不恢复旧自动值。</p>
        </details>
      )}
    </section>
  );
}
