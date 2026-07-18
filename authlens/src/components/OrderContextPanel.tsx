import './OrderContextPanel.css';
import {
  CHART_ITEMS,
  ASSESSMENTS,
} from '../data/mockCase';
import type { ApiCriterionAssessment, ApiChartItem } from '../api/client';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  onCheckReadiness: () => void;
  onAddClarification: () => void;
  assessments?: ApiCriterionAssessment[];
  chartItems?: ApiChartItem[];
  isLoading?: boolean;
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
  assessments: liveAssessments,
  chartItems: liveChartItems,
  isLoading = false,
}: Props) {
  const activeAssessments = liveAssessments ?? ASSESSMENTS;
  const activeChartItems  = liveChartItems  ?? CHART_ITEMS;

  const statusCounts = hasRunAnalysis
    ? activeAssessments.reduce(
        (acc, a) => {
          const st = liveAssessments
            ? a.status
            : (hasClarification ? (a as any).status_after ?? a.status : a.status);
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
            <button
              className="btn btn-primary ocp-action-btn"
              onClick={onCheckReadiness}
              disabled={isLoading}
            >
              {isLoading ? 'Analyzing…' : 'Check Readiness'}
            </button>
          </div>
        ) : (
          <div className="ocp-summary animate-fade-in">
            {statusCounts && (
              <>
                <div className="ocp-summary-met">
                  {statusCounts.met ?? 0} of 7 requirements supported
                </div>
                {(statusCounts.weak ?? 0) > 0 && (
                  <div className="ocp-summary-item ocp-summary-weak">
                    {statusCounts.weak} needs clarification
                  </div>
                )}
                {(statusCounts.missing ?? 0) > 0 && (
                  <div className="ocp-summary-item ocp-summary-missing">
                    {statusCounts.missing} not supported
                  </div>
                )}
                {!hasClarification && (
                  <button className="ocp-clinician-link" onClick={onAddClarification}>
                    Needs clinician input →
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* ── Clinical context: FHIR items ── */}
      <div className="ocp-section ocp-chart-section">
        <div className="ocp-section-header">Clinical Context</div>
        <div className="ocp-chart-list">
          {activeChartItems.map((item) => {
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
