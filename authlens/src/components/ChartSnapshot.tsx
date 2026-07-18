import './ChartSnapshot.css';

export default function ChartSnapshot() {
  return (
    <aside className="chart-snapshot">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-header-title">Chart Context</span>
          <span className="chip chip-blue" style={{ fontSize: '9px' }}>Live</span>
        </div>
        <div className="cs-body">

          <section className="cs-section">
            <div className="section-label">Problems</div>
            <div className="cs-item">
              <span className="fhir-tag">FHIR: Condition</span>
              <div className="cs-item-text">Chronic low back pain</div>
              <div className="cs-item-meta">M54.5 · Active</div>
            </div>
            <div className="cs-item">
              <span className="fhir-tag">FHIR: Condition</span>
              <div className="cs-item-text">Hypertension</div>
              <div className="cs-item-meta">I10 · Active</div>
            </div>
          </section>

          <div className="divider" />

          <section className="cs-section">
            <div className="section-label">Medications</div>
            <div className="cs-item">
              <span className="fhir-tag">FHIR: MedRequest</span>
              <div className="cs-item-text">Ibuprofen 600 mg tablet</div>
              <div className="cs-item-meta">1 tab PO q6h PRN pain · Active</div>
            </div>
          </section>

          <div className="divider" />

          <section className="cs-section">
            <div className="section-label">Orders / Referrals</div>
            <div className="cs-item cs-item--highlight">
              <span className="fhir-tag">FHIR: ServiceRequest</span>
              <div className="cs-item-text">
                Lumbar Spine MRI w/o contrast
                <span className="pa-required-tag">PA Required</span>
              </div>
              <div className="cs-item-meta">Draft · Routine · Outpatient</div>
            </div>
            <div className="cs-item">
              <span className="fhir-tag">FHIR: ServiceRequest</span>
              <div className="cs-item-text">Physical therapy referral</div>
              <div className="cs-item-meta">Pending</div>
            </div>
          </section>

          <div className="divider" />

          <section className="cs-section">
            <div className="section-label">Recent Results</div>
            <div className="cs-empty">
              <span className="cs-empty-icon">○</span>
              No recent lumbar imaging found
            </div>
          </section>

          <div className="divider" />

          <section className="cs-section">
            <div className="section-label">Coverage</div>
            <div className="cs-item">
              <div className="cs-item-text">BlueCross PPO</div>
              <div className="cs-item-meta">Member ID: BCBS-902184</div>
            </div>
          </section>

        </div>
      </div>
    </aside>
  );
}
