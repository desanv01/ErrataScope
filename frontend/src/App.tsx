import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api";
import type {
  Anchor,
  CaseContext,
  Claim,
  Coverage,
  Draft,
  Review,
  ReviewHistory,
  ReviewSummary,
} from "./types";

type LoadState = "loading" | "ready" | "error";

function shortHash(value: string | null | undefined): string {
  if (!value) return "not recorded";
  return `${value.slice(0, 10)}…${value.slice(-6)}`;
}

function pageLabel(anchor: Anchor): string {
  if (anchor.geometry_kind === "synthetic_not_located") return "synthetic excerpt · no PDF location";
  const physical = `page ${anchor.page_index + 1}`;
  return anchor.printed_page_label ? `${physical} · printed ${anchor.printed_page_label}` : physical;
}

function statusLabel(current: Review | null): string {
  if (!current) return "Needs review";
  return current.decision === "reviewed" ? "Reviewed" : "Rejected";
}

function claimLabel(field: string): string {
  return field.replaceAll("_", " ");
}

function CitationChips({
  claim,
  activeKey,
  onSelect,
}: {
  claim: Claim;
  activeKey: string;
  onSelect: (key: string) => void;
}) {
  return (
    <div className="citations" aria-label={`Citations for ${claimLabel(claim.field)}`}>
      {claim.citations.map((citation) => (
        <button
          key={citation.anchor_key}
          type="button"
          className={`citation ${activeKey === citation.anchor_key ? "is-active" : ""}`}
          onClick={() => onSelect(citation.anchor_key)}
          aria-pressed={activeKey === citation.anchor_key}
          title={citation.text ?? citation.anchor_key}
        >
          {citation.missing ? "missing anchor" : pageLabel({
            geometry_kind: citation.geometry_kind,
            page_index: (citation.physical_page ?? 1) - 1,
            printed_page_label: citation.printed_page_label ?? null,
          } as Anchor)}
        </button>
      ))}
    </div>
  );
}

export default function App() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");
  const [cases, setCases] = useState<CaseContext[]>([]);
  const [activeCase, setActiveCase] = useState<CaseContext | null>(null);
  const [projectName, setProjectName] = useState("");
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [reviews, setReviews] = useState<ReviewHistory | null>(null);
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [section, setSection] = useState("");
  const [activeAnchor, setActiveAnchor] = useState("");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const sourceRef = useRef<HTMLDivElement | null>(null);

  const selectedCoverage = useMemo(
    () => coverage.filter((entry) => entry.section === section),
    [coverage, section],
  );
  const sectionAnchors = useMemo(
    () =>
      anchors
        .filter((anchor) => anchor.section === section && anchor.context_kind === null)
        .sort((a, b) => a.page_index - b.page_index || a.bbox.top - b.bbox.top),
    [anchors, section],
  );
  const contextAnchors = useMemo(
    () =>
      anchors.filter((anchor) =>
        ["source_identity", "revision_header", "status_legend", "footnote"].includes(
          anchor.context_kind ?? "",
        ),
      ),
    [anchors],
  );
  const unselected = useMemo(
    () => coverage.filter((entry) => entry.reason === "not_selected"),
    [coverage],
  );
  const currentReview = reviews?.items.at(-1) ?? null;
  const currentSummary = summary;

  async function loadCase(selected: CaseContext) {
    setActiveCase(selected);
    setNote("");
    setState("loading");
    setNotice("");
    try {
      const [anchorData, coverageData, draftDataRaw, reviewData, summaryData] = await Promise.all([
        api.getAnchors(selected.extraction_id),
        api.getCoverage(selected.extraction_id),
        api.getDraft(selected.draft_id),
        api.getReviews(selected.draft_id),
        api.getSummary(selected.draft_id),
      ]);
      const anchorMap = new Map(anchorData.map((anchor) => [anchor.anchor_key, anchor]));
      const draftData: Draft = {
        ...draftDataRaw,
        draft: {
          ...draftDataRaw.draft,
          claims: draftDataRaw.draft.claims.map((claim) => ({
            ...claim,
            citations: claim.citations.map((citation: unknown) => {
              if (typeof citation === "string") {
                const anchor = anchorMap.get(citation);
                return {
                  anchor_key: citation,
                  text: anchor?.text,
                  physical_page: anchor?.geometry_kind === "located" ? anchor.page_index + 1 : null,
                  geometry_kind: anchor?.geometry_kind,
                  printed_page_label: anchor?.printed_page_label,
                  section: anchor?.section,
                  block_role: anchor?.block_role,
                  context_kind: anchor?.context_kind,
                  missing: !anchor,
                };
              }
              return citation as Claim["citations"][number];
            }),
          })),
        },
      };
      setAnchors(anchorData);
      setCoverage(coverageData);
      setDraft(draftData);
      setReviews(reviewData);
      setSummary(summaryData);
      const firstSection = selected.selected_entries.find((entry) =>
        coverageData.some((row) => row.section === entry && row.status === "supported"),
      ) ?? selected.selected_entries[0] ?? "";
      setSection(firstSection);
      const firstClaim = draftData.draft.claims[0];
      setActiveAnchor(firstClaim?.citations[0]?.anchor_key ?? "");
      setState("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load this workspace.");
      setState("error");
    }
  }

  async function initialise() {
    setState("loading");
    setError("");
    try {
      await api.bootstrap();
      const projects = await api.listProjects();
      const contexts = [];
      for (const project of projects) {
        try {
          const context = await api.submissionContext(project.id);
          if (context.cases.length > 0) contexts.push(context);
        } catch {
          // A project without an accessible submission case is skipped.
        }
      }
      const preferred =
        contexts.find((context) =>
          context.cases.some((item) => item.kind === "recorded_live"),
        ) ?? contexts[0];
      if (preferred) {
        setProjectName(preferred.project_name || "Project");
        setCases(preferred.cases);
        const initial =
          preferred.cases.find((item) => item.kind === "recorded_live") ??
          preferred.default_case ??
          preferred.cases[0];
        await loadCase(initial);
        return;
      }
      setError("No authorized recorded interpretation is available yet.");
      setState("error");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The local API is unavailable.");
      setState("error");
    }
  }

  useEffect(() => {
    void initialise();
  }, []);

  function chooseAnchor(key: string) {
    const anchor = anchors.find((item) => item.anchor_key === key);
    if (anchor?.section && activeCase?.selected_entries.includes(anchor.section)) {
      setSection(anchor.section);
    }
    setActiveAnchor(key);
    setNotice("");
    window.setTimeout(() => {
      const element = document.getElementById(`anchor-${key}`);
      const details = element?.closest("details");
      if (details) details.open = true;
      element?.scrollIntoView({ block: "center", behavior: "smooth" });
    }, 0);
  }

  async function submitReview(decision: "reviewed" | "rejected") {
    if (!draft || !reviews) return;
    if (!note.trim()) {
      setNotice("Add a short review note before recording a decision.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      await api.recordReview(draft.id, {
        expected_revision: reviews.current_revision,
        expected_response_hash: draft.response_hash,
        decision,
        note,
      });
      setNote("");
      setNotice(
        decision === "reviewed"
          ? "Interpretation review recorded. This is human acknowledgement, not an accepted rule."
          : "Interpretation rejection recorded. The draft remains available in history.",
      );
      const [reviewData, summaryData] = await Promise.all([
        api.getReviews(draft.id),
        api.getSummary(draft.id),
      ]);
      setReviews(reviewData);
      setSummary(summaryData);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Review could not be recorded.";
      setNotice(message);
      if (caught instanceof api.ApiError && caught.status === 409) {
        const [reviewData, summaryData] = await Promise.all([
          api.getReviews(draft.id),
          api.getSummary(draft.id),
        ]);
        setReviews(reviewData);
        setSummary(summaryData);
      }
    } finally {
      setBusy(false);
    }
  }

  async function exportSummary(format: "json" | "markdown") {
    if (!draft) return;
    setExporting(true);
    setNotice("");
    try {
      await api.downloadSummary(draft.id, format);
    } catch (caught) {
      setNotice(caught instanceof Error ? caught.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  if (state === "loading") {
    return (
      <div className="full-state" role="status" aria-live="polite">
        <div className="loading-mark" />
        <h1>Loading the recorded interpretation</h1>
        <p>Authorizing locally and reading the source, citations and review history.</p>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="full-state" role="alert">
        <p className="eyebrow">Workspace unavailable</p>
        <h1>{error}</h1>
        <p>This local development build requires the API and its generated local dev identity.</p>
        <button type="button" className="primary" onClick={() => void initialise()}>
          Retry workspace
        </button>
      </div>
    );
  }

  return (
    <div className="workspace">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            ◈
          </span>
          <strong>ErrataScope</strong>
          <span className="divider" aria-hidden="true" />
          <span className="crumb">{projectName || "Project"}</span>
          <span className="crumb">/</span>
          <span className="crumb strong">
            {activeCase?.document_id ?? "Source"} {activeCase?.revision ?? ""}
          </span>
        </div>
        <div className="top-actions">
          {activeCase && (
            <span className={`provenance ${activeCase.kind}`}>{activeCase.label}</span>
          )}
          <button
            type="button"
            className="secondary"
            onClick={() => void exportSummary("json")}
            disabled={exporting || !currentSummary}
          >
            Export JSON
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => void exportSummary("markdown")}
            disabled={exporting || !currentSummary}
          >
            Export Markdown
          </button>
        </div>
      </header>

      <div className="body-grid">
        <aside className="navigator" aria-label="Sources and selected entries">
          <div className="navigator-head">
            <p className="eyebrow">Sources</p>
            {cases.length > 1 && (
              <label className="case-select">
                <span className="sr-only">Choose demonstration case</span>
                <select
                  value={activeCase?.draft_id ?? ""}
                  onChange={(event) => {
                    const next = cases.find((item) => item.draft_id === event.target.value);
                    if (next) void loadCase(next);
                  }}
                >
                  {cases.map((item) => (
                    <option key={item.draft_id} value={item.draft_id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <div className="source-identity">
            <span className="source-icon" aria-hidden="true">
              ▤
            </span>
            <div>
              <strong>{activeCase?.document_id ?? "Unknown document"}</strong>
              <p>{activeCase?.revision ?? "Revision not stated"}</p>
              <p className="muted">{activeCase?.manufacturer ?? "Manufacturer not stated"}</p>
            </div>
          </div>
          <div className="nav-section">
            <p className="nav-label">Selected</p>
            {activeCase?.selected_entries.map((entry) => {
              const row = coverage.find((item) => item.section === entry);
              return (
                <button
                  key={entry}
                  type="button"
                  className={`entry-link ${section === entry ? "is-active" : ""}`}
                  onClick={() => setSection(entry)}
                  aria-current={section === entry ? "true" : undefined}
                >
                  <span aria-hidden="true">▤</span>
                  <span>
                    {entry}
                    <small>{row?.title ?? "Selected entry"}</small>
                  </span>
                </button>
              );
            })}
          </div>
          <div className="nav-section">
            <p className="nav-label">Source context</p>
            {contextAnchors.slice(0, 6).map((anchor) => (
              <button
                key={anchor.anchor_key}
                type="button"
                className="context-link"
                onClick={() => chooseAnchor(anchor.anchor_key)}
              >
                {anchor.context_kind?.replaceAll("_", " ") ?? "context"}
              </button>
            ))}
          </div>
          <div className="nav-foot">
            <p>
              <span aria-hidden="true">ⓘ</span> Selected entries only. Inventory is incomplete.
            </p>
          </div>
        </aside>

        <main className="source-pane" ref={sourceRef}>
          <div className="pane-head">
            <div>
              <p className="eyebrow">Source context</p>
              <h1>
                {activeCase?.document_id ?? "Source"} ·{" "}
                {section ? `Section ${section}` : "Selected extraction"}
              </h1>
            </div>
            <div className="pane-meta">
              <span>{selectedCoverage[0]?.title ?? activeCase?.selected_entries.join(", ")}</span>
              <span className="muted">{activeCase?.synthetic ? "Original synthetic text · no PDF location" : "Physical page shown per excerpt"}</span>
            </div>
          </div>

          <div className="paper" aria-label="Actual extracted source excerpts">
            <div className="paper-title">
              <h2>{activeCase?.document_id ?? "Unknown document"}</h2>
              <p>{activeCase?.manufacturer ?? "Identity not stated"}</p>
            </div>
            <div className="paper-rule" />
            {sectionAnchors.length === 0 && (
              <div className="empty-excerpt">
                <h3>No located excerpt for this entry</h3>
                <p>
                  The real extraction did not produce located text for this selection. Nothing has
                  been invented to fill the pane.
                </p>
              </div>
            )}
            {sectionAnchors.map((anchor) => (
              <article
                key={anchor.anchor_key}
                id={`anchor-${anchor.anchor_key}`}
                className={`excerpt ${anchor.block_role} ${
                  activeAnchor === anchor.anchor_key ? "is-active" : ""
                }`}
              >
                <div className="excerpt-meta">
                  <span>{pageLabel(anchor)}</span>
                  <span>{anchor.block_role}</span>
                  <code>{anchor.anchor_key}</code>
                </div>
                <p>{anchor.text}</p>
              </article>
            ))}
            <details className="context-block">
              <summary>Document identity, revision headers and legends</summary>
              {contextAnchors.map((anchor) => (
                <article
                  key={anchor.anchor_key}
                  id={`anchor-${anchor.anchor_key}`}
                  className={`context-excerpt ${
                    activeAnchor === anchor.anchor_key ? "is-active" : ""
                  }`}
                >
                  <div className="excerpt-meta">
                    <span>{anchor.context_kind?.replaceAll("_", " ")}</span>
                    <span>{pageLabel(anchor)}</span>
                  </div>
                  <p>{anchor.text}</p>
                </article>
              ))}
            </details>
          </div>

          <div className="anchor-foot">
            <div>
              <p className="eyebrow">Source version</p>
              <p>
                SHA-256 <code>{shortHash(activeCase?.source_sha256)}</code> ·{" "}
                {activeCase?.authority ?? "authority unknown"}
              </p>
            </div>
            <div>
              <p className="eyebrow">Coverage</p>
              <p>
                {summary?.coverage.selected_entries_supported.length ?? 0} supported of{" "}
                {coverage.length} detected entries · inventory incomplete
              </p>
            </div>
          </div>
        </main>

        <aside className="review-pane" aria-label="Interpretation and review">
          <div className="review-head">
            <div>
              <p className="eyebrow">Interpretation</p>
              <h2>Source-grounded draft</h2>
            </div>
            <span className={`review-badge ${currentReview?.decision ?? "pending"}`}>
              {currentReview?.decision === "reviewed" ? "✓ " : ""}
              {statusLabel(currentReview)}
            </span>
          </div>
          <p className="review-sub">
            Inspect each claim against its source before acknowledging. A review is not an accepted
            executable rule.
          </p>

          {activeCase && (
            <section className={`provenance-card ${activeCase.kind}`} aria-label="Provenance">
              <div>
                <span className="label">Provenance</span>
                <strong>{activeCase.label}</strong>
              </div>
              <dl>
                <div>
                  <dt>Prompt</dt>
                  <dd>{draft?.prompt_version ?? activeCase.prompt_version}</dd>
                </div>
                <div>
                  <dt>Provider request</dt>
                  <dd>{activeCase.provider_request_id ?? "not recorded"}</dd>
                </div>
                <div>
                  <dt>Usage</dt>
                  <dd>
                    {summary?.draft.usage
                      ? `${String(summary.draft.usage.prompt_tokens ?? "?")} in / ${String(
                          summary.draft.usage.completion_tokens ?? "?",
                        )} out`
                      : "not recorded"}
                  </dd>
                </div>
                <div>
                  <dt>Response hash</dt>
                  <dd>
                    <code>{shortHash(draft?.response_hash ?? activeCase.review?.response_hash)}</code>
                  </dd>
                </div>
              </dl>
              {activeCase.kind === "recorded_live" && (
                <p className="limitation">
                  Recorded live result. The stored response is normalized JSON; the original
                  wire-byte hash is bound but cannot be re-derived from that artifact.
                </p>
              )}
              {activeCase.kind === "synthetic_offline" && (
                <p className="limitation">
                  Synthetic/offline example. This is not a manufacturer live result and does not
                  prove a live omission case.
                </p>
              )}
            </section>
          )}

          <section className="claims" aria-label="Interpretation claims">
            <div className="claims-head">
              <h3>Claims and citations</h3>
              <span>{draft?.draft.claims.length ?? 0} claims</span>
            </div>
            {draft?.draft.claims.map((claim, index) => (
              <article className="claim" key={`${claim.field}-${index}`}>
                <div className="claim-title">
                  <span className="claim-index">{index + 1}</span>
                  <strong>{claimLabel(claim.field)}</strong>
                  <span className={`claim-status ${claim.status}`}>{claim.status}</span>
                </div>
                <p>{claim.value}</p>
                <CitationChips claim={claim} activeKey={activeAnchor} onSelect={chooseAnchor} />
              </article>
            ))}
          </section>

          {draft && draft.draft.unresolved_fields.length > 0 && (
            <section className="unresolved" aria-label="Unresolved information">
              <div className="unresolved-head">
                <span aria-hidden="true">△</span>
                <h3>Unresolved information</h3>
              </div>
              <ul>
                {draft.draft.unresolved_fields.map((field) => (
                  <li key={field}>{claimLabel(field)}</li>
                ))}
              </ul>
              <p>
                These fields are not established by the supplied source subset. Null or unknown is
                not false.
              </p>
            </section>
          )}

          <section className="coverage-card" aria-label="Coverage status">
            <div>
              <h3>Coverage</h3>
              <p>
                Selected scope only. {unselected.length} detected entries were not selected and are
                not assessed.
              </p>
            </div>
            <div className="coverage-stats">
              <span>
                <strong>{coverage.length}</strong> detected
              </span>
              <span>
                <strong>{activeCase?.selected_entries.length ?? 0}</strong> selected
              </span>
              <span>
                <strong>{summary?.coverage.selected_entries_supported.length ?? 0}</strong>{" "}
                supported
              </span>
            </div>
            {unselected.length > 0 && (
              <details>
                <summary>Unselected entries</summary>
                <ul>
                  {unselected.map((entry) => (
                    <li key={entry.section}>
                      {entry.section} — {entry.title ?? "untitled"}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>

          <section className="review-form" aria-label="Interpretation review">
            <label htmlFor="review-note">
              <span>Review note</span>
              <small>Required, 1–2000 characters. Recorded with your current role.</small>
            </label>
            <textarea
              id="review-note"
              value={note}
              maxLength={2000}
              rows={4}
              placeholder="Note your source observations, uncertainty, or reason for rejection…"
              onChange={(event) => setNote(event.target.value)}
            />
            <div className="review-actions">
              <button
                type="button"
                className="primary"
                disabled={busy || !note.trim()}
                onClick={() => void submitReview("reviewed")}
              >
                Review draft
              </button>
              <button
                type="button"
                className="danger"
                disabled={busy || !note.trim()}
                onClick={() => void submitReview("rejected")}
              >
                Reject
              </button>
            </div>
            {notice && (
              <p className="notice" role="status">
                {notice}
              </p>
            )}
            <div className="review-history">
              <div className="claims-head">
                <h3>Review history</h3>
                <span>Revision {reviews?.current_revision ?? 0}</span>
              </div>
              {reviews?.items.length ? (
                reviews.items.map((review) => (
                  <div className="history-row" key={review.id}>
                    <span className={`decision ${review.decision}`}>{review.decision}</span>
                    <div>
                      <p>{review.note}</p>
                      <small>
                        Revision {review.revision} · {new Date(review.created_at).toLocaleString()}
                      </small>
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted">No interpretation review has been recorded.</p>
              )}
            </div>
          </section>

          <footer className="pane-foot">
            <span aria-hidden="true">ⓘ</span>
            Assessment requires a reviewed rule and project facts; that feature is not included in
            this fallback.
          </footer>
        </aside>
      </div>
      <footer className="statusbar">
        <span>▤ Draft interpretation</span>
        <span>Cited selected scope only · no applicability claim</span>
      </footer>
    </div>
  );
}
