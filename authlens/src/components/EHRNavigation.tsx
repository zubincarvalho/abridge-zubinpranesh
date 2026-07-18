import './EHRNavigation.css';

/* Epic-style icon-only left nav rail */

function IconChart() {
  return (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="currentColor">
      <rect x="1.5" y="9.5" width="3" height="6" rx="1"/>
      <rect x="7"   y="5.5" width="3" height="10" rx="1"/>
      <rect x="12.5" y="2.5" width="3" height="13" rx="1"/>
    </svg>
  );
}

function IconFlask() {
  return (
    <svg width="16" height="17" viewBox="0 0 16 17" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5.5 2h5M7 2v5l-4 7.5c-.5 1 .2 1.8 1 1.8h8c.8 0 1.5-.8 1-1.8L10 7V2"/>
      <line x1="3.5" y1="11" x2="12.5" y2="11"/>
    </svg>
  );
}

function IconDoc() {
  return (
    <svg width="14" height="17" viewBox="0 0 14 17" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="1" width="11" height="15" rx="1.5"/>
      <line x1="4" y1="5"  x2="10" y2="5"/>
      <line x1="4" y1="8"  x2="10" y2="8"/>
      <line x1="4" y1="11" x2="7.5" y2="11"/>
    </svg>
  );
}

function IconPill() {
  return (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round">
      <rect x="2" y="6" width="13" height="5" rx="2.5"/>
      <line x1="8.5" y1="6" x2="8.5" y2="11"/>
    </svg>
  );
}

function IconClipboard() {
  return (
    <svg width="14" height="17" viewBox="0 0 14 17" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="3" width="11" height="13" rx="1.5"/>
      <path d="M4.5 1.5h5c.3 0 .5.2.5.5v1.5h-6V2c0-.3.2-.5.5-.5z"/>
      <line x1="4" y1="8"  x2="10" y2="8"/>
      <line x1="4" y1="11" x2="10" y2="11"/>
    </svg>
  );
}

function IconShieldCheck() {
  return (
    <svg width="15" height="17" viewBox="0 0 15 17" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7.5 1L14 4v5c0 4-2.8 6.8-6.5 8C4.3 15.8 1 13 1 9V4z"/>
      <polyline points="4.5,8.5 6.5,10.5 10.5,6.5"/>
    </svg>
  );
}

function IconGrid() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round">
      <rect x="1.5" y="1.5" width="5" height="5" rx="1"/>
      <rect x="9.5" y="1.5" width="5" height="5" rx="1"/>
      <rect x="1.5" y="9.5" width="5" height="5" rx="1"/>
      <rect x="9.5" y="9.5" width="5" height="5" rx="1"/>
    </svg>
  );
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  active?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'summary',   label: 'Summary',          icon: <IconGrid />      },
  { id: 'chart',     label: 'Chart',             icon: <IconChart />     },
  { id: 'results',   label: 'Results',           icon: <IconFlask />     },
  { id: 'notes',     label: 'Clinical Notes',    icon: <IconDoc />       },
  { id: 'meds',      label: 'Medications',       icon: <IconPill />      },
  { id: 'orders',    label: 'Orders',            icon: <IconClipboard />, badge: '1' },
  { id: 'pa',        label: 'Prior Auth',        icon: <IconShieldCheck />, active: true, badge: 'PA' },
];

export default function EHRNavigation() {
  return (
    <nav className="ehr-nav" aria-label="Epic activity navigation">
      <div className="ehr-nav-logo">
        <div className="ehr-logo-mark">E</div>
      </div>

      <ul className="ehr-nav-list" role="list">
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              className={`ehr-nav-item${item.active ? ' active' : ''}`}
              title={item.label}
              aria-label={item.label}
              aria-current={item.active ? 'page' : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.badge && (
                <span className={`nav-badge${item.active ? ' nav-badge--active' : ''}`}>
                  {item.badge}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>

      <div className="ehr-nav-footer">
        <button className="provider-avatar-btn" title="Morris, Kelsey MD">
          KM
        </button>
      </div>
    </nav>
  );
}
