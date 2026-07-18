import './EHRNavigation.css';

const NAV_ITEMS = [
  { id: 'summary', label: 'Summary', icon: '▤' },
  { id: 'chart', label: 'Chart Review', icon: '📊' },
  { id: 'notes', label: 'Notes', icon: '📝', active: true },
  { id: 'results', label: 'Results', icon: '🧪' },
  { id: 'medications', label: 'Medications', icon: '💊' },
  { id: 'orders', label: 'Orders', icon: '📋', badge: '1' },
  { id: 'referrals', label: 'Referrals', icon: '↗' },
  { id: 'authorizations', label: 'Authorizations', icon: '🔐', badge: 'PA' },
  { id: 'messages', label: 'Messages', icon: '✉' },
];

export default function EHRNavigation() {
  return (
    <nav className="ehr-nav">
      <div className="ehr-nav-logo">
        <div className="ehr-logo-mark">NM</div>
        <div className="ehr-logo-text">NorthviewEHR</div>
      </div>

      <div className="ehr-nav-section-label">Encounter</div>
      <ul className="ehr-nav-list">
        {NAV_ITEMS.map((item) => (
          <li key={item.id} className={`ehr-nav-item ${item.active ? 'active' : ''}`}>
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </li>
        ))}
      </ul>

      <div className="ehr-nav-footer">
        <div className="provider-avatar">KM</div>
        <div className="provider-info">
          <div className="provider-name">Kelsey Morris, MD</div>
          <div className="provider-org">Northview Medical Group</div>
        </div>
      </div>
    </nav>
  );
}
