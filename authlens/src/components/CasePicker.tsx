import { useState, useEffect } from 'react';
import './CasePicker.css';
import { listScenarios, createCase, getDemoCase, type DemoScenario, type ApiCase } from '../api/client';

type Props = {
  onCaseSelected: (c: ApiCase) => void;
};

const RISK_CLS: Record<string, string> = {
  low: 'picker-risk-low',
  medium: 'picker-risk-medium',
  high: 'picker-risk-high',
};
const OUTCOME_CLS: Record<string, string> = {
  approved: 'chip-met',
  gap: 'chip-weak',
  high_risk: 'chip-missing',
};

export default function CasePicker({ onCaseSelected }: Props) {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listScenarios()
      .then(setScenarios)
      .catch(() => {
        // backend unavailable — fall back to the canonical demo case
        getDemoCase().then(onCaseSelected).catch(() => setError('Backend unavailable.'));
      });
  }, [onCaseSelected]);

  async function handleSelect(scenario: DemoScenario) {
    setLoadingId(scenario.scenario_id);
    setError(null);
    try {
      let caseData: ApiCase;
      if (scenario.fixture_id === 'lumbar_mri_prior_auth') {
        caseData = await getDemoCase();
      } else {
        caseData = await createCase(scenario.fixture_id);
      }
      onCaseSelected(caseData);
    } catch (err) {
      setError(`Could not load case: ${(err as Error).message}`);
      setLoadingId(null);
    }
  }

  return (
    <div className="picker-overlay">
      <div className="picker-container">
        <div className="picker-header">
          <div className="picker-brand">
            <div className="picker-al-logo">AL</div>
            <div>
              <div className="picker-brand-name">AuthLens</div>
              <div className="picker-brand-sub">Prior Authorization Readiness · Powered by Abridge AI</div>
            </div>
          </div>
          <div className="picker-policy-badge">
            Policy MHP-IMG-2201 · Meridian Health Plans (fictional) · Lumbar Spine MRI
          </div>
        </div>

        <h2 className="picker-title">Select a Demo Case</h2>
        <p className="picker-subtitle">
          Each case is analyzed against the same real payer policy criteria using AI.
          Cases marked "Abridge Data" use real synthetic encounter transcripts and FHIR records.
        </p>

        {error && <div className="picker-error">{error}</div>}

        <div className="picker-cards">
          {scenarios.length === 0 && !error && (
            <div className="picker-loading">Loading scenarios…</div>
          )}
          {scenarios.map((s) => {
            const isLoading = loadingId === s.scenario_id;
            return (
              <div key={s.scenario_id} className={`picker-card picker-card--${s.risk_level}`}>
                <div className="picker-card-top">
                  <div className="picker-card-badges">
                    <span className={`chip ${OUTCOME_CLS[s.expected_outcome]}`}>
                      {s.expected_outcome_label}
                    </span>
                    {s.is_real_data && (
                      <span className="chip chip-purple">Abridge Data</span>
                    )}
                  </div>
                  <div className={`picker-risk-dot ${RISK_CLS[s.risk_level]}`} />
                </div>

                <div className="picker-card-title">{s.title}</div>
                <div className="picker-patient">{s.patient_display}</div>
                <div className="picker-visit">{s.visit_summary}</div>

                <div className="picker-card-divider" />

                <div className="picker-service-row">
                  <span className="picker-label">Service</span>
                  <span className="picker-value">{s.requested_service}</span>
                </div>
                <div className="picker-service-row">
                  <span className="picker-label">Policy</span>
                  <span className="picker-value">{s.policy_id} · {s.payer}</span>
                </div>

                <p className="picker-desc">{s.description}</p>

                <button
                  className="btn btn-primary picker-select-btn"
                  onClick={() => handleSelect(s)}
                  disabled={loadingId !== null}
                >
                  {isLoading ? (
                    <><span className="picker-spinner" /> Loading case…</>
                  ) : (
                    'Select this case →'
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <div className="picker-footer">
          All data is synthetic. No real patient information is used. Policy criteria are hackathon-authored
          and do not represent any real payer policy.
        </div>
      </div>
    </div>
  );
}
