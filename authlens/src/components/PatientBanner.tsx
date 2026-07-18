import './PatientBanner.css';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
};

export default function PatientBanner({ hasRunAnalysis, hasClarification }: Props) {
  const authLensStatus = !hasRunAnalysis
    ? { label: 'Not Analyzed', cls: 'chip-gray' }
    : hasClarification
    ? { label: 'Ready for Human Review', cls: 'chip-met' }
    : { label: 'Needs Clarification', cls: 'chip-orange' };

  const priorAuthStatus = hasClarification
    ? { label: 'Ready for Review', cls: 'chip-teal' }
    : { label: 'Required', cls: 'chip-orange' };

  return (
    <header className="patient-banner">
      <div className="banner-patient">
        <div className="banner-name">
          Jordan Rivera
          <span className="synthetic-badge">SYNTHETIC</span>
        </div>
        <div className="banner-meta">
          <span>Female</span>
          <span className="sep">·</span>
          <span>DOB 04/02/1979</span>
          <span className="sep">·</span>
          <span>ID pt-demo-001</span>
        </div>
        <div className="banner-encounter">
          <span className="enc-label">Encounter:</span> Clinic visit — chronic low back pain follow-up
          <span className="sep">·</span>
          <span className="enc-label">Coverage:</span> Meridian Health Plans (fictional)
        </div>
      </div>

      <div className="banner-chips">
        <div className="banner-chip-group">
          <span className="chip-label">Visit Status</span>
          <span className="chip chip-blue">Open Encounter</span>
        </div>
        <div className="banner-chip-group">
          <span className="chip-label">Abridge Note</span>
          <span className="chip chip-purple">Draft · AI Generated</span>
        </div>
        <div className="banner-chip-group">
          <span className="chip-label">AuthLens</span>
          <span className={`chip ${authLensStatus.cls}`}>{authLensStatus.label}</span>
        </div>
        <div className="banner-chip-group">
          <span className="chip-label">Prior Auth</span>
          <span className={`chip ${priorAuthStatus.cls}`}>{priorAuthStatus.label}</span>
        </div>
      </div>
    </header>
  );
}
