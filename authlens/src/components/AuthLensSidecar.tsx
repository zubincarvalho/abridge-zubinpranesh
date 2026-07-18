import './AuthLensSidecar.css';
import { ASSESSMENTS, READINESS_INITIAL, READINESS_POST_CLARIFICATION } from '../data/mockCase';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  onCheckReadiness: () => void;
  onSourceClick: (sourceId: string, excerpt?: string) => void;
};

const STATUS_ICON: Record<string, string> = { met: '✓', weak: '!', missing: '✕' };
const STATUS_CLS: Record<string, string> = {
  met: 'criterion-met',
  weak: 'criterion-weak',
  missing: 'criterion-missing',
};

export default function AuthLensSidecar({
  hasRunAnalysis,
  hasClarification,
  onCheckReadiness,
  onSourceClick,
}: Props) {
  const readiness = hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL;
  const score = hasRunAnalysis ? readiness.score : 0;
  const status = hasClarification
    ? 'Ready for human review'
    : hasRunAnalysis
    ? 'Needs clarification'
    : 'Not analyzed';
  const statusCls = hasClarification
    ? 'status-ready'
    : hasRunAnalysis
    ? 'status-needs'
    : 'status-idle';
  const barColor =
    score >= 90 ? '#15803d' : score >= 70 ? '#d97706' : '#9ca3af';

  return (
    <aside className="authlens-sidecar panel">
      <div className="panel-header authlens-header">
        <div className="authlens-brand">
          <div className="authlens-logo">AL</div>
          <div>
            <div className="authlens-title">AuthLens</div>
            <div className="authlens-subtitle">Prior Auth Readiness</div>
          </div>
        </div>
      </div>

      <div className="authlens-body">
        <div className="authlens-trigger-card">
          <div className="section-label">Triggered by Order</div>
          <div className="trigger-order">MRI Lumbar Spine w/o contrast (CPT 72148)</div>
          <div className="trigger-meta">
            <div>
              <span className="section-label">Payer</span> Meridian Health Plans (fictional)
            </div>
            <div>
              <span className="section-label">Policy</span> MHP-IMG-2201
            </div>
          </div>
        </div>

        <div className="authlens-score-card">
          <div className="score-row">
            <span className="section-label">Readiness</span>
            <span className="score-value" style={{ color: barColor }}>
              {hasRunAnalysis ? `${score}%` : '—'}
            </span>
          </div>
          {hasRunAnalysis && (
            <div className="score-bar-track">
              <div
                className="score-bar-fill"
                style={{ width: `${score}%`, background: barColor }}
              />
            </div>
          )}
          {hasRunAnalysis && (
            <div className="score-summary-row">
              <span className="score-detail-chip score-met">{readiness.criteria_met} met</span>
              <span className="score-detail-chip score-weak">{readiness.criteria_weak} weak</span>
              <span className="score-detail-chip score-missing">
                {readiness.criteria_missing} missing
              </span>
            </div>
          )}
          <div className={`authlens-status-badge ${statusCls}`}>{status}</div>
        </div>

        {!hasRunAnalysis && (
          <button className="btn btn-primary check-btn" onClick={onCheckReadiness}>
            <span>⚡</span> Check Readiness
          </button>
        )}

        {hasRunAnalysis && (
          <div className="criteria-list animate-fade-in">
            <div className="section-label" style={{ marginBottom: '6px' }}>
              Criteria — 7 of 7 evaluated
            </div>
            {ASSESSMENTS.map((a) => {
              const s = hasClarification ? a.status_after : a.status;
              const firstEv = a.evidence[0];
              return (
                <button
                  key={a.criterion_id}
                  className={`criterion-item ${STATUS_CLS[s]}`}
                  onClick={() =>
                    onSourceClick(
                      firstEv?.source_id ?? 'note-001',
                      firstEv?.excerpt
                    )
                  }
                >
                  <span className="criterion-icon">{STATUS_ICON[s]}</span>
                  <span className="criterion-label">
                    <span className="criterion-id">{a.criterion_id}</span>{' '}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {hasRunAnalysis && !hasClarification && (
          <div className="authlens-hint animate-fade-in">
            <span>⬇</span> See evidence matrix below for gaps and suggested questions.
          </div>
        )}

        {hasClarification && (
          <div className="authlens-ready-note animate-fade-in">
            <span className="ready-icon">✓</span>
            Clarification received. Ready for human review.
          </div>
        )}

        <div className="divider" />

        <div className="authlens-policy-info">
          <div className="section-label">Payer Policy Reference</div>
          <div className="policy-detail">
            Meridian Health Plans (fictional) · MHP-IMG-2201
          </div>
          <div className="policy-criteria-count">7 medical necessity criteria evaluated</div>
        </div>
      </div>
    </aside>
  );
}
