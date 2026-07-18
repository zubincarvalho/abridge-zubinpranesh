import './OrderContextPanel.css';
import {
  CHART_ITEMS,
  ASSESSMENTS,
  READINESS_INITIAL,
  READINESS_POST_CLARIFICATION,
} from '../data/mockCase';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  onCheckReadiness: () => void;
  onAddClarification: () => void;
};

const CATEGORY_LABEL: Record<string, string> = {
  condition:       'Condition',
  observation:     'Exam Finding',
  medication:      'Medication',
  referral:        'Referral',
  service_request: 'Order',
};

const EXCLUDED_ID = 'fhir-cond-002';

export default function OrderContextPanel({
  hasRunAnalysis,
  hasClarification,
  onCheckReadiness,
  onAddClarification,
}: Props) {
  const readiness = hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL;
  const scoreColor =
    readiness.score >= 90 ? '#15803d' :
    readiness.score >= 75 ? '#c07000' : '#b91c1c';

  const statusCounts = hasRunAnalysis
    ? ASSESSMENTS.reduce(
        (acc, a) => {
          const st = hasClarification ? a.status_after : a.status;
          acc[st] = (acc[st] ?? 0) + 1;
          return acc;
        },
        {} as Record<string, number>,
      )
    : null;

  return (
    <div className="ocp">
      {/* ── Order details ── */}
      <div className="ocp-section">
        <div className="ocp-section-header">Pending Order</div>
        <div className="ocp-order-card">
          <div className="ocp-service-name">MRI Lumbar Spine w/o Contrast</div>
          <div className="ocp-order-tags">
            <span className="ocp-cpt-tag">CPT 72148</span>
            <span className="ocp-auth-tag">Prior Auth Required</span>
          </div>
          <div className="ocp-kv">
            <span className="ocp-key">Payer</span>
            <span>Meridian Health Plans (fictional)</span>
          </div>
          <div className="ocp-kv">
            <span className="ocp-key">Policy</span>
            <span className="ocp-policy-id">MHP-IMG-2201</span>
          </div>
        </div>
      </div>

      {/* ── AuthLens status ── */}
      <div className="ocp-section ocp-authlens-section">
        <div className="ocp-section-header ocp-section-header--authlens">
          <span className="ocp-al-title">⚡ AuthLens</span>
          <span className="ocp-ai-pill">AI</span>
        </div>

        {!hasRunAnalysis ? (
          <div className="ocp-idle">
            <p className="ocp-idle-text">
              Ready to analyze encounter against 7 criteria in MHP-IMG-2201 and surface linked evidence.
            </p>
            <button className="btn btn-primary ocp-action-btn" onClick={onCheckReadiness}>
              Check Readiness
            </button>
          </div>
        ) : (
          <div className="ocp-status animate-fade-in">
            <div className="ocp-score-row">
              <span className="ocp-score" style={{ color: scoreColor }}>
                {readiness.score}%
              </span>
              <div className="ocp-score-meta">
                <span className="ocp-score-label">Readiness</span>
                <span className={`chip ${
                  readiness.overall_denial_risk === 'high'   ? 'chip-missing' :
                  readiness.overall_denial_risk === 'medium' ? 'chip-weak'    : 'chip-met'
                }`}>
                  {readiness.overall_denial_risk} denial risk
                </span>
              </div>
            </div>

            <div className="score-bar-track ocp-score-bar">
              <div
                className="score-bar-fill"
                style={{ width: `${readiness.score}%`, background: scoreColor }}
              />
            </div>

            {statusCounts && (
              <div className="ocp-criteria-row">
                {statusCounts.met    != null && <span className="chip chip-met">{statusCounts.met} met</span>}
                {statusCounts.weak   != null && <span className="chip chip-weak">{statusCounts.weak} weak</span>}
                {statusCounts.missing != null && statusCounts.missing > 0 && (
                  <span className="chip chip-missing">{statusCounts.missing} missing</span>
                )}
              </div>
            )}

            {!hasClarification && (
              <button className="btn btn-teal ocp-action-btn" onClick={onAddClarification}>
                Add Clarification
              </button>
            )}

            {hasClarification && (
              <div className="ocp-ready-banner">
                <span>✓</span> Ready for Human Review
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Clinical context: FHIR items ── */}
      <div className="ocp-section ocp-chart-section">
        <div className="ocp-section-header">Clinical Context</div>
        <div className="ocp-chart-list">
          {CHART_ITEMS.map((item) => {
            const excluded = item.source_id === EXCLUDED_ID;
            return (
              <div
                key={item.source_id}
                className={`ocp-chart-item${excluded ? ' ocp-chart-item--excluded' : ''}`}
              >
                <div className="ocp-chart-item-top">
                  <span className="fhir-tag">{CATEGORY_LABEL[item.category] ?? item.category}</span>
                  {excluded && <span className="ocp-excluded-badge">Excluded</span>}
                </div>
                <div className="ocp-chart-item-text">{item.display}</div>
                {item.detail && (
                  <div className="ocp-chart-item-detail">{item.detail}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
