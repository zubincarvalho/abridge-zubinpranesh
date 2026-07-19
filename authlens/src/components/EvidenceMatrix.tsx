import { useState, Fragment } from 'react';
import './EvidenceMatrix.css';
import {
  ASSESSMENTS,
  POLICY_CRITERIA,
  READINESS_INITIAL,
  READINESS_POST_CLARIFICATION,
} from '../data/mockCase';
import type {
  ApiCriterionAssessment,
  ApiPolicyCriterion,
  ApiPayerPolicy,
  ApiEvidenceItem,
} from '../api/client';

type Props = {
  hasClarification: boolean;
  onSourceClick: (sourceId: string, excerpt?: string) => void;
  /** Click-to-source: jump to the note and pulse the span (falls back to the
   *  drawer for non-note sources). Defaults to onSourceClick when omitted. */
  onFocusSource?: (sourceId: string, excerpt?: string) => void;
  assessments?: ApiCriterionAssessment[];
  criteria?: ApiPolicyCriterion[];
  policy?: ApiPayerPolicy;
};

const STATUS_LABEL: Record<string, string> = {
  met: 'Supported',
  weak: 'Needs clarification',
  missing: 'Not supported',
  conflicting: 'Conflicting',
  not_applicable: 'Not applicable',
};
const STATUS_CLS: Record<string, string> = {
  met: 'chip-met',
  weak: 'chip-weak',
  missing: 'chip-missing',
  conflicting: 'chip-weak',
  not_applicable: 'chip-gray',
};

const SOURCE_TYPE_LABEL: Record<string, string> = {
  encounter_note: 'Encounter note',
  encounter_transcript: 'Transcript',
  fhir_resource: 'Clinical data (FHIR)',
  clinician_clarification: 'Clinician clarification',
  payer_policy: 'Payer policy',
};

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High confidence',
  moderate: 'Moderate confidence',
  low: 'Low confidence',
};

export default function EvidenceMatrix({
  hasClarification,
  onSourceClick,
  assessments: liveAssessments,
  criteria: liveCriteria,
  policy,
  onFocusSource,
}: Props) {
  const focusSource = onFocusSource ?? onSourceClick;
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const activeAssessments = liveAssessments ?? ASSESSMENTS;
  const activeCriteria = liveCriteria ?? POLICY_CRITERIA;

  const counts = activeAssessments.reduce(
    (acc, a) => {
      const st = liveAssessments ? a.status : (hasClarification ? (a as any).status_after ?? a.status : a.status);
      acc[st] = (acc[st] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  const readiness = liveAssessments
    ? { criteria_met: counts.met ?? 0, criteria_weak: (counts.weak ?? 0) + (counts.conflicting ?? 0), criteria_missing: counts.missing ?? 0 }
    : (hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL);

  const criteriaMap = Object.fromEntries(activeCriteria.map((c) => [c.criterion_id, c]));

  const policyId = policy?.policy_id ?? 'MHP-IMG-2201';
  const policyTitle = policy?.policy_title ?? 'Medical Necessity Policy: Lumbar Spine MRI';
  const payerName = policy?.payer_name;

  const statusLine = [
    `${readiness.criteria_met} supported`,
    readiness.criteria_weak > 0 ? `${readiness.criteria_weak} needs clarification` : null,
    readiness.criteria_missing > 0 ? `${readiness.criteria_missing} not supported` : null,
  ].filter(Boolean).join(' · ');

  return (
    <div className="evidence-matrix panel">
      <div className="panel-header">
        <div className="matrix-header-left">
          <span className="panel-header-title">Evidence &amp; Medical-Necessity Criteria</span>
          <span className="matrix-policy-ref">{statusLine}</span>
        </div>
      </div>

      <div className="matrix-provenance">
        <span className="matrix-prov-icon">📋</span>
        <span>
          These <strong>{activeCriteria.length} criteria</strong> are parsed directly from payer
          policy <strong>{policyId}</strong>
          {payerName ? <> · {payerName}</> : null} — <em>{policyTitle}</em>. Click any criterion to
          see the verbatim policy requirement and the exact evidence AuthLens cited.
        </span>
      </div>

      <div className="matrix-table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th style={{ width: 24 }} aria-label="expand" />
              <th>ID</th>
              <th>Criterion</th>
              <th>Status</th>
              <th>Key Evidence</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {activeAssessments.map((a) => {
              const status = liveAssessments
                ? a.status
                : (hasClarification ? ((a as any).status_after ?? a.status) : a.status);
              const evidence: ApiEvidenceItem[] = liveAssessments
                ? a.evidence
                : (hasClarification ? ((a as any).evidence_after ?? a.evidence) : a.evidence);
              const firstEv = evidence[0];
              const criterion = criteriaMap[a.criterion_id] as ApiPolicyCriterion | undefined;
              const isOpen = expanded.has(a.criterion_id);
              const rationale = (a as any).rationale as string | undefined;

              return (
                <Fragment key={a.criterion_id}>
                  <tr
                    className={`matrix-row matrix-row--${status}${isOpen ? ' matrix-row--open' : ''}`}
                    onClick={() => toggle(a.criterion_id)}
                  >
                    <td className="matrix-expand-cell">
                      <span className={`matrix-chevron${isOpen ? ' matrix-chevron--open' : ''}`}>▸</span>
                    </td>
                    <td className="matrix-crit-id">{a.criterion_id}</td>
                    <td className="matrix-criterion">{criterion?.label ?? a.criterion_id}</td>
                    <td>
                      <span className={`chip ${STATUS_CLS[status] ?? 'chip-gray'}`}>
                        {STATUS_LABEL[status] ?? status}
                      </span>
                    </td>
                    <td>
                      {firstEv ? (
                        <button
                          className="matrix-evidence-link"
                          onClick={(e) => { e.stopPropagation(); focusSource(firstEv.source_id, firstEv.excerpt); }}
                          title={firstEv.excerpt}
                        >
                          {firstEv.excerpt.length > 80 ? firstEv.excerpt.slice(0, 80) + '…' : firstEv.excerpt}
                        </button>
                      ) : (
                        <span className="matrix-fix-none">—</span>
                      )}
                    </td>
                    <td>
                      {firstEv ? (
                        <button
                          className="matrix-source-link"
                          onClick={(e) => { e.stopPropagation(); onSourceClick(firstEv.source_id, firstEv.excerpt); }}
                        >
                          <span className="matrix-source-type">
                            {SOURCE_TYPE_LABEL[firstEv.source_type] ?? firstEv.source_type}
                          </span>
                          <span className="matrix-link-icon">↗</span>
                        </button>
                      ) : (
                        <span className="matrix-fix-none">—</span>
                      )}
                    </td>
                  </tr>

                  {isOpen && (
                    <tr className="matrix-detail-row">
                      <td colSpan={6}>
                        <div className="matrix-detail animate-fade-in">
                          <div className="matrix-detail-origin">
                            <span className="origin-badge">Criterion {a.criterion_id}</span>
                            <span>
                              parsed from <strong>{criterion?.policy_id ?? policyId}</strong>
                              {criterion?.category ? <> · category: <code>{criterion.category}</code></> : null}
                            </span>
                          </div>

                          {criterion?.requirement && (
                            <div className="matrix-detail-block">
                              <div className="detail-h">Policy requirement (verbatim)</div>
                              <blockquote className="detail-requirement">“{criterion.requirement}”</blockquote>
                              {criterion.applicability_note && (
                                <div className="detail-applicability">
                                  Applicability: {criterion.applicability_note}
                                </div>
                              )}
                            </div>
                          )}

                          {rationale && (
                            <div className="matrix-detail-block">
                              <div className="detail-h">AuthLens assessment</div>
                              <p className="detail-rationale">{rationale}</p>
                            </div>
                          )}

                          <div className="matrix-detail-block">
                            <div className="detail-h">Cited evidence ({evidence.length})</div>
                            {evidence.length === 0 ? (
                              <div className="detail-noevidence">
                                No supporting documentation was located. This is reported as a gap —
                                never inferred.
                              </div>
                            ) : (
                              <ul className="detail-evidence-list">
                                {evidence.map((ev) => (
                                  <li key={ev.evidence_id} className="detail-evidence-item">
                                    <button
                                      className="detail-evidence-btn"
                                      onClick={(e) => { e.stopPropagation(); focusSource(ev.source_id, ev.excerpt); }}
                                    >
                                      <span className="detail-ev-excerpt">“{ev.excerpt}”</span>
                                      <span className="detail-ev-meta">
                                        <span className="detail-ev-src">
                                          {SOURCE_TYPE_LABEL[ev.source_type] ?? ev.source_type}
                                        </span>
                                        <span className={`detail-ev-conf detail-ev-conf--${ev.confidence}`}>
                                          {CONFIDENCE_LABEL[ev.confidence] ?? ev.confidence}
                                        </span>
                                        <span className="matrix-link-icon">↗</span>
                                      </span>
                                    </button>
                                    {ev.note && <div className="detail-ev-note">⚠ {ev.note}</div>}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
