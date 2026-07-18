import './ChartSnapshot.css';
import { CHART_ITEMS } from '../data/mockCase';

const CATEGORY_LABEL: Record<string, string> = {
  condition: 'Condition',
  observation: 'Observation',
  medication: 'MedRequest',
  referral: 'ServiceRequest',
  service_request: 'ServiceRequest',
};

const CATEGORY_SECTION: Record<string, string> = {
  condition: 'Problems',
  observation: 'Exam Findings',
  medication: 'Medications',
  referral: 'Orders / Referrals',
  service_request: 'Orders / Referrals',
};

const SECTION_ORDER = ['Problems', 'Exam Findings', 'Medications', 'Orders / Referrals'];

export default function ChartSnapshot() {
  const sections: Record<string, typeof CHART_ITEMS> = {};
  for (const item of CHART_ITEMS) {
    const section = CATEGORY_SECTION[item.category] ?? 'Other';
    if (!sections[section]) sections[section] = [];
    sections[section].push(item);
  }

  return (
    <aside className="chart-snapshot">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-header-title">Chart Context</span>
          <span className="chip chip-blue" style={{ fontSize: '9px' }}>FHIR</span>
        </div>
        <div className="cs-body">

          {SECTION_ORDER.filter((s) => sections[s]).map((sectionName, si) => (
            <div key={sectionName}>
              {si > 0 && <div className="divider" />}
              <section className="cs-section">
                <div className="section-label">{sectionName}</div>
                {sections[sectionName].map((item) => {
                  const excluded = item.source_id === 'fhir-cond-002';
                  const isMriOrder = item.source_id === 'fhir-sr-mri-001';
                  return (
                    <div key={item.source_id} className={`cs-item${isMriOrder ? ' cs-item--highlight' : ''}`}>
                      <span className="fhir-tag">FHIR: {CATEGORY_LABEL[item.category] ?? item.category}</span>
                      <div className="cs-item-text">
                        {item.display}
                        {isMriOrder && <span className="pa-required-tag">PA Required</span>}
                        {excluded && (
                          <span className="pa-required-tag" style={{ background: '#fee2e2', color: '#991b1b', borderColor: '#fca5a5' }}>
                            Excluded
                          </span>
                        )}
                      </div>
                      <div className="cs-item-meta">
                        {excluded ? (
                          <span style={{ color: '#b91c1c', fontSize: '10px' }}>
                            Excluded — unrelated condition (minimum-necessary disclosure)
                          </span>
                        ) : (
                          <span>{item.detail}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </section>
            </div>
          ))}

          <div className="divider" />

          <section className="cs-section">
            <div className="section-label">Coverage</div>
            <div className="cs-item">
              <div className="cs-item-text">Meridian Health Plans (fictional)</div>
              <div className="cs-item-meta">Policy MHP-IMG-2201 · Lumbar Spine MRI</div>
            </div>
          </section>

        </div>
      </div>
    </aside>
  );
}
