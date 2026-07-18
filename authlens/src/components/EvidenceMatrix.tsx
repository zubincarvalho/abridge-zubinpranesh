import './EvidenceMatrix.css';
import {
  ASSESSMENTS,
  POLICY_CRITERIA,
  READINESS_INITIAL,
  READINESS_POST_CLARIFICATION,
} from '../data/mockCase';

type Props = {
  hasClarification: boolean;
  onSourceClick: (sourceId: string, excerpt?: string) => void;
};

const STATUS_LABEL: Record<string, string> = {
  met: 'Met',
  weak: 'Weak',
  missing: 'Missing',
};
const STATUS_CLS: Record<string, string> = {
  met: 'chip-met',
  weak: 'chip-weak',
  missing: 'chip-missing',
};

const SOURCE_TYPE_LABEL: Record<string, string> = {
  encounter_note: 'Encounter Note',
  encounter_transcript: 'Transcript',
  fhir_resource: 'FHIR',
  clinician_clarification: 'Clarification',
};

export default function EvidenceMatrix({ hasClarification, onSourceClick }: Props) {
  const readiness = hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL;
  const beforeScore = READINESS_INITIAL.score;
  const afterScore = READINESS_POST_CLARIFICATION.score;

  const criteriaMap = Object.fromEntries(
    POLICY_CRITERIA.map((c) => [c.criterion_id, c])
  );

  return (
    <div className="evidence-matrix panel">
      <div className="panel-header">
        <div className="matrix-header-left">
          <span className="panel-header-title">Authorization Readiness</span>
          <span className="matrix-policy-ref">
            Meridian Health Plans (fictional) · MHP-IMG-2201 · {readiness.criteria_met} met /{' '}
            {readiness.criteria_weak} weak / {readiness.criteria_missing} missing
          </span>
        </div>
        <div className="matrix-scores">
          <div className="matrix-score-item">
            <span className="matrix-score-label">Before clarification</span>
            <span className="matrix-score-value matrix-score-before">{beforeScore}%</span>
          </div>
          <div className="matrix-score-arrow">→</div>
          <div className="matrix-score-item">
            <span className="matrix-score-label">After clarification</span>
            <span
              className={`matrix-score-value ${
                hasClarification ? 'matrix-score-after' : 'matrix-score-after-dim'
              }`}
            >
              {afterScore}%
            </span>
          </div>
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
            {ASSESSMENTS.map((a) => {
              const status = hasClarification ? a.status_after : a.status;
              const evidence = hasClarification ? a.evidence_after : a.evidence;
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
