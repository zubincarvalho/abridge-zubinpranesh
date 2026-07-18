import './AuthLensSidecar.css';
import { EVIDENCE_ROWS } from '../data/mockCase';
import type { SourceDetail } from '../data/mockCase';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  onCheckReadiness: () => void;
  onSourceClick: (source: SourceDetail) => void;
};

const STATUS_ICON: Record<string, string> = { met: '✓', weak: '!', missing: '✕' };
const STATUS_CLS: Record<string, string> = { met: 'criterion-met', weak: 'criterion-weak', missing: 'criterion-missing' };

export default function AuthLensSidecar({ hasRunAnalysis, hasClarification, onCheckReadiness, onSourceClick }: Props) {
  const score = hasClarification ? 94 : hasRunAnalysis ? 58 : 0;
  const status = hasClarification ? 'Ready for human review' : hasRunAnalysis ? 'Needs clarification' : 'Not analyzed';
  const statusCls = hasClarification ? 'status-ready' : hasRunAnalysis ? 'status-needs' : 'status-idle';
  const barColor = score >= 90 ? '#15803d' : score >= 50 ? '#d97706' : '#9ca3af';

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
          <div className="trigger-order">MRI Lumbar Spine w/o contrast</div>
          <div className="trigger-meta">
            <div><span className="section-label">Payer</span> BlueCross PPO</div>
            <div><span className="section-label">Policy</span> Lumbar Spine MRI Medical Necessity</div>
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
              <div className="score-bar-fill" style={{ width: `${score}%`, background: barColor }} />
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
            <div className="section-label" style={{ marginBottom: '6px' }}>Criteria Checklist</div>
            {EVIDENCE_ROWS.map((row) => {
              const s = hasClarification ? row.statusAfter : row.status;
              return (
                <button
                  key={row.id}
                  className={`criterion-item ${STATUS_CLS[s]}`}
                  onClick={() => onSourceClick(row.sourceDetail)}
                >
                  <span className="criterion-icon">{STATUS_ICON[s]}</span>
                  <span className="criterion-label">{row.criterion}</span>
                </button>
              );
            })}
          </div>
        )}

        {hasRunAnalysis && !hasClarification && (
          <div className="authlens-hint animate-fade-in">
            <span>⬇</span> See evidence matrix below for details and suggested questions.
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
          <div className="policy-detail">BlueCross PPO · MRI Spine Policy 2024-L07</div>
          <div className="policy-criteria-count">5 medical necessity criteria evaluated</div>
        </div>
      </div>
    </aside>
  );
}
