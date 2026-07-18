import './PatientBanner.css';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
};

const ACTIVITY_TABS = [
  { id: 'chart',   label: 'Chart Review' },
  { id: 'results', label: 'Results' },
  { id: 'notes',   label: 'Clinical Notes' },
  { id: 'orders',  label: 'Orders' },
  { id: 'pa',      label: 'Prior Auth Assistant', active: true },
];

export default function PatientBanner({ hasRunAnalysis, hasClarification }: Props) {
  const statusLabel = !hasRunAnalysis
    ? null
    : hasClarification
    ? { text: 'Ready for Review', cls: 'status-chip--ready' }
    : { text: 'Needs Clarification', cls: 'status-chip--pending' };

  return (
    <header className="patient-header">
      {/* Epic chrome bar — app-level navigation */}
      <div className="epic-chrome">
        <div className="epic-chrome-left">
          <span className="epic-wordmark">epic</span>
          <span className="epic-sep">›</span>
          <span className="epic-breadcrumb">Encounters</span>
          <span className="epic-sep">›</span>
          <span className="epic-patient-crumb">Rivera, Jordan</span>
        </div>
        <div className="epic-chrome-right">
          <span className="epic-env-tag">SANDBOX</span>
          <div className="epic-user">
            <span className="epic-user-avatar">KM</span>
            <span className="epic-user-label">Morris, Kelsey MD</span>
          </div>
        </div>
      </div>

      {/* Patient identity + encounter strip */}
      <div className="patient-strip">
        <div className="patient-id-row">
          <span className="patient-name">Rivera, Jordan</span>
          <span className="patient-dot">·</span>
          <span className="patient-demo">47F</span>
          <span className="patient-dot">·</span>
          <span className="patient-demo">DOB 04/02/1979</span>
          <span className="patient-dot">·</span>
          <span className="patient-demo">MRN pt-demo-001</span>
          <span className="synthetic-badge">SYNTHETIC</span>
          {statusLabel && (
            <span className={`patient-status-chip ${statusLabel.cls}`}>
              AuthLens: {statusLabel.text}
            </span>
          )}
        </div>
        <div className="patient-meta-row">
          <span className="meta-item">
            <span className="meta-key">Encounter</span>
            Clinic Visit — Chronic Low Back Pain
          </span>
          <span className="meta-sep">|</span>
          <span className="meta-item">
            <span className="meta-key">Provider</span>
            Morris, Kelsey MD
          </span>
          <span className="meta-sep">|</span>
          <span className="meta-item">
            <span className="meta-key">Payer</span>
            Meridian Health Plans (fictional)
          </span>
          <span className="meta-sep">|</span>
          <span className="meta-item enc-status-open">
            Open Encounter
          </span>
        </div>
      </div>

      {/* Activity tab row — Epic Hyperspace activity selector */}
      <div className="activity-tab-row" role="tablist" aria-label="Chart activities">
        {ACTIVITY_TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={tab.active ?? false}
            className={`activity-tab${tab.active ? ' activity-tab--active' : ''}`}
          >
            {tab.label}
            {tab.id === 'pa' && hasRunAnalysis && (
              <span className={`tab-status-dot${hasClarification ? ' dot--green' : ' dot--amber'}`} />
            )}
          </button>
        ))}
      </div>
    </header>
  );
}
