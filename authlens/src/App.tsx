import { useState } from 'react';
import './index.css';
import './App.css';

import PatientBanner     from './components/PatientBanner';
import EHRNavigation     from './components/EHRNavigation';
import OrderContextPanel from './components/OrderContextPanel';
import AbridgeNotePanel  from './components/AbridgeNotePanel';
import AgentTimeline     from './components/AgentTimeline';
import EvidenceMatrix    from './components/EvidenceMatrix';
import GapResolutionPanel from './components/GapResolutionPanel';
import PriorAuthFormDraft from './components/PriorAuthFormDraft';
import DisclosurePanel   from './components/DisclosurePanel';
import SourceDrawer      from './components/SourceDrawer';

type CenterTab = 'evidence' | 'note' | 'agents';
type RightTab  = 'form'     | 'disclosure';

type SelectedSource = { sourceId: string; excerpt?: string };

export default function App() {
  const [hasRunAnalysis,  setHasRunAnalysis]  = useState(false);
  const [hasClarification, setHasClarification] = useState(false);
  const [selectedSource,  setSelectedSource]  = useState<SelectedSource | undefined>();
  const [centerTab, setCenterTab] = useState<CenterTab>('evidence');
  const [rightTab,  setRightTab]  = useState<RightTab>('form');

  function handleCheckReadiness() {
    setHasRunAnalysis(true);
    setCenterTab('evidence');
  }

  function handleAddClarification() {
    setHasClarification(true);
    setCenterTab('evidence');
    setRightTab('form');
  }

  function handleSourceClick(sourceId: string, excerpt?: string) {
    setSelectedSource({ sourceId, excerpt });
  }

  return (
    <div className="app-shell">
      <PatientBanner
        hasRunAnalysis={hasRunAnalysis}
        hasClarification={hasClarification}
      />

      <div className="app-body">
        <EHRNavigation />

        <main className="app-main">
          {/* Activity header bar */}
          <div className="pa-activity-bar">
            <div className="pa-activity-title">
              <span className="pa-activity-icon">⚡</span>
              Prior Authorization Assistant
              <span className="pa-activity-model">AuthLens · Abridge AI</span>
            </div>
            <div className="pa-activity-meta">
              <span className="chip chip-gray">MHP-IMG-2201</span>
              <span className="chip chip-purple">CPT 72148</span>
              <span className="pa-synthetic-tag">SYNTHETIC DATA</span>
            </div>
          </div>

          {/* 3-column PA workspace */}
          <div className="pa-workspace">

            {/* ── Left column: Order context + AuthLens status ── */}
            <aside className="pa-col pa-col-left">
              <OrderContextPanel
                hasRunAnalysis={hasRunAnalysis}
                hasClarification={hasClarification}
                onCheckReadiness={handleCheckReadiness}
                onAddClarification={handleAddClarification}
              />
            </aside>

            {/* ── Center column: Evidence / Note / Agent log ── */}
            <section className="pa-col pa-col-center">
              {hasRunAnalysis ? (
                <>
                  <div className="pa-col-tabs">
                    {(
                      [
                        { key: 'evidence', label: 'Evidence Checklist' },
                        { key: 'note',     label: 'Note View'          },
                        { key: 'agents',   label: 'Agent Log'          },
                      ] as { key: CenterTab; label: string }[]
                    ).map(({ key, label }) => (
                      <button
                        key={key}
                        className={`pa-col-tab${centerTab === key ? ' pa-col-tab--active' : ''}`}
                        onClick={() => setCenterTab(key)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div className="pa-col-body">
                    {centerTab === 'evidence' && (
                      <div className="pa-col-content animate-fade-in">
                        <EvidenceMatrix
                          hasClarification={hasClarification}
                          onSourceClick={handleSourceClick}
                        />
                        <GapResolutionPanel
                          hasClarification={hasClarification}
                          onAddClarification={handleAddClarification}
                        />
                      </div>
                    )}
                    {centerTab === 'note' && (
                      <div className="pa-col-content animate-fade-in">
                        <AbridgeNotePanel
                          hasClarification={hasClarification}
                          onPhraseClick={handleSourceClick}
                        />
                      </div>
                    )}
                    {centerTab === 'agents' && (
                      <div className="pa-col-content animate-fade-in">
                        <AgentTimeline
                          hasRunAnalysis={hasRunAnalysis}
                          hasClarification={hasClarification}
                        />
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="pa-center-idle">
                  <div className="pa-idle-card">
                    <div className="pa-idle-icon">🔍</div>
                    <div className="pa-idle-heading">Evidence retrieval pending</div>
                    <div className="pa-idle-body">
                      AuthLens will analyze this encounter against <strong>7 policy criteria</strong>{' '}
                      in MHP-IMG-2201 and surface linked evidence from the Abridge clinical note.
                    </div>
                    <div className="pa-idle-hint">
                      Click <strong>Check Readiness</strong> in the left panel to begin.
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ── Right column: Auth form + Disclosure ── */}
            <aside className="pa-col pa-col-right">
              {hasRunAnalysis ? (
                <>
                  <div className="pa-col-tabs">
                    {(
                      [
                        { key: 'form',        label: 'Auth Form'   },
                        { key: 'disclosure',  label: 'Disclosure'  },
                      ] as { key: RightTab; label: string }[]
                    ).map(({ key, label }) => (
                      <button
                        key={key}
                        className={`pa-col-tab${rightTab === key ? ' pa-col-tab--active' : ''}`}
                        onClick={() => setRightTab(key)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div className="pa-col-body">
                    {rightTab === 'form' && (
                      <div className="pa-col-content animate-fade-in">
                        <PriorAuthFormDraft
                          hasClarification={hasClarification}
                          onSourceClick={handleSourceClick}
                        />
                      </div>
                    )}
                    {rightTab === 'disclosure' && (
                      <div className="pa-col-content animate-fade-in">
                        <DisclosurePanel onSourceClick={handleSourceClick} />
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="pa-right-idle">
                  <div className="pa-right-idle-icon">📄</div>
                  <div className="pa-right-idle-title">Auth Packet</div>
                  <div className="pa-right-idle-body">
                    AuthLens will draft the authorization packet once evidence retrieval is complete.
                  </div>
                </div>
              )}
            </aside>
          </div>
        </main>
      </div>

      {selectedSource && (
        <SourceDrawer
          sourceId={selectedSource.sourceId}
          excerpt={selectedSource.excerpt}
          onClose={() => setSelectedSource(undefined)}
        />
      )}
    </div>
  );
}
