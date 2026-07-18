import './EvidenceMatrix.css';
import {
  ASSESSMENTS,
  POLICY_CRITERIA,
  READINESS_INITIAL,
  READINESS_POST_CLARIFICATION,
} from '../data/mockCase';
import type { ApiCriterionAssessment, ApiPolicyCriterion } from '../api/client';

type Props = {
  hasClarification: boolean;
  onSourceClick: (sourceId: string, excerpt?: string) => void;
  assessments?: ApiCriterionAssessment[];
  criteria?: ApiPolicyCriterion[];
};

const STATUS_LABEL: Record<string, string> = {
  met: 'Supported',
  weak: 'Needs clarification',
  missing: 'Not supported',
};
const STATUS_CLS: Record<string, string> = {
  met: 'chip-met',
  weak: 'chip-weak',
  missing: 'chip-missing',
};

const SOURCE_TYPE_LABEL: Record<string, string> = {
  encounter_note: 'Encounter note',
  encounter_transcript: 'Transcript',
  fhir_resource: 'Clinical data',
  clinician_clarification: 'Clinician clarification',
  payer_policy: 'Payer policy',
};

export default function EvidenceMatrix({ hasClarification, onSourceClick, assessments: liveAssessments, criteria: liveCriteria }: Props) {
  // Use live data when available, fall back to mock constants
  const activeAssessments = liveAssessments ?? ASSESSMENTS;
  const activeCriteria    = liveCriteria    ?? POLICY_CRITERIA;

  // Derive readiness counts from actual assessments (not pre-computed summaries)
  const counts = activeAssessments.reduce(
    (acc, a) => {
      const st = liveAssessments ? a.status : (hasClarification ? (a as any).status_after ?? a.status : a.status);
      acc[st] = (acc[st] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  const readiness = liveAssessments
    ? { criteria_met: counts.met ?? 0, criteria_weak: counts.weak ?? 0, criteria_missing: counts.missing ?? 0 }
    : (hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL);

  const criteriaMap = Object.fromEntries(
    activeCriteria.map((c) => [c.criterion_id, c])
  );

  const statusLine = [
    `${readiness.criteria_met} supported`,
    readiness.criteria_weak > 0 ? `${readiness.criteria_weak} needs clarification` : null,
    readiness.criteria_missing > 0 ? `${readiness.criteria_missing} not supported` : null,
  ].filter(Boolean).join(' · ');

  return (
    <div className="evidence-matrix panel">
      <div className="panel-header">
        <div className="matrix-header-left">
          <span className="panel-header-title">Evidence</span>
          <span className="matrix-policy-ref">{statusLine} — MHP-IMG-2201</span>
        </div>
      </div>

      <div className="matrix-table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Criterion</th>
              <th>Status</th>
              <th>Key Evidence</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {activeAssessments.map((a) => {
              // Live data is always current state; mock data has status_after
              const status = liveAssessments
                ? a.status
                : (hasClarification ? ((a as any).status_after ?? a.status) : a.status);
              const evidence = liveAssessments
                ? a.evidence
                : (hasClarification ? ((a as any).evidence_after ?? a.evidence) : a.evidence);
              const firstEv = evidence[0];
              const criterion = criteriaMap[a.criterion_id];

              return (
                <tr key={a.criterion_id} className={`matrix-row matrix-row--${status}`}>
                  <td className="matrix-crit-id">{a.criterion_id}</td>
                  <td className="matrix-criterion">{criterion?.label ?? a.criterion_id}</td>
                  <td>
                    <span className={`chip ${STATUS_CLS[status]}`}>{STATUS_LABEL[status]}</span>
                  </td>
                  <td>
                    {firstEv ? (
                      <button
                        className="matrix-evidence-link"
                        onClick={() => onSourceClick(firstEv.source_id, firstEv.excerpt)}
                        title={firstEv.excerpt}
                      >
                        {firstEv.excerpt.length > 80
                          ? firstEv.excerpt.slice(0, 80) + '…'
                          : firstEv.excerpt}
                      </button>
                    ) : (
                      <span className="matrix-fix-none">—</span>
                    )}
                  </td>
                  <td>
                    {firstEv ? (
                      <button
                        className="matrix-source-link"
                        onClick={() => onSourceClick(firstEv.source_id, firstEv.excerpt)}
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
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
