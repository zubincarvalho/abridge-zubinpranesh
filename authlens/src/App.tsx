import { useState } from 'react';
import './index.css';
import './App.css';

import PatientBanner from './components/PatientBanner';
import EHRNavigation from './components/EHRNavigation';
import ChartSnapshot from './components/ChartSnapshot';
import AbridgeNotePanel from './components/AbridgeNotePanel';
import AuthLensSidecar from './components/AuthLensSidecar';
import AgentTimeline from './components/AgentTimeline';
import EvidenceMatrix from './components/EvidenceMatrix';
import GapResolutionPanel from './components/GapResolutionPanel';
import PriorAuthFormDraft from './components/PriorAuthFormDraft';
import DisclosurePanel from './components/DisclosurePanel';
import SourceDrawer from './components/SourceDrawer';
import { READINESS_INITIAL, READINESS_POST_CLARIFICATION } from './data/mockCase';

type TabKey = 'evidence' | 'form' | 'disclosure' | 'agents';

type SelectedSource = {
  sourceId: string;
  excerpt?: string;
};

export default function App() {
  const [hasRunAnalysis, setHasRunAnalysis] = useState(false);
  const [hasClarification, setHasClarification] = useState(false);
  const [selectedSource, setSelectedSource] = useState<SelectedSource | undefined>();
  const [activeTab, setActiveTab] = useState<TabKey>('evidence');

  function handleCheckReadiness() {
    setHasRunAnalysis(true);
    setActiveTab('evidence');
  }

  function handleAddClarification() {
    setHasClarification(true);
    setActiveTab('evidence');
  }

  function handleSourceClick(sourceId: string, excerpt?: string) {
    setSelectedSource({ sourceId, excerpt });
  }

  function closeDrawer() {
    setSelectedSource(undefined);
  }

  const readiness = hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL;

  return (
    <div className="app-shell">
      <PatientBanner hasRunAnalysis={hasRunAnalysis} hasClarification={hasClarification} />

      <div className="app-body">
        <EHRNavigation />

        <main className="app-main">
          {/* Top section: chart snapshot + note + sidecar */}
          <div className="workspace-row">
            <ChartSnapshot />

            <AbridgeNotePanel
              hasClarification={hasClarification}
              onPhraseClick={handleSourceClick}
            />

            <AuthLensSidecar
              hasRunAnalysis={hasRunAnalysis}
              hasClarification={hasClarification}
              onCheckReadiness={handleCheckReadiness}
              onSourceClick={handleSourceClick}
            />
          </div>

          {/* Bottom details area */}
          {hasRunAnalysis && (
            <div className="detail-area animate-fade-in">
              {/* Tab bar */}
              <div className="tab-bar">
                <div className="tab-bar-tabs">
                  {(
                    [
                      { key: 'evidence', label: 'Evidence Matrix' },
                      { key: 'form', label: 'Prior Auth Form' },
                      { key: 'disclosure', label: 'Disclosure Review' },
                      { key: 'agents', label: 'Agent Log' },
                    ] as { key: TabKey; label: string }[]
                  ).map(({ key, label }) => (
                    <button
                      key={key}
                      className={`tab-btn ${activeTab === key ? 'tab-btn--active' : ''}`}
                      onClick={() => setActiveTab(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="tab-bar-meta">
                  {hasClarification ? (
                    <span className="chip chip-met">
                      Readiness: {READINESS_POST_CLARIFICATION.score}%
                    </span>
                  ) : (
                    <span className="chip chip-orange">
                      Readiness: {READINESS_INITIAL.score}%
                    </span>
                  )}
                  <span
                    className={`chip ${
                      readiness.overall_denial_risk === 'high'
                        ? 'chip-missing'
                        : readiness.overall_denial_risk === 'medium'
                        ? 'chip-weak'
                        : 'chip-met'
                    }`}
                  >
                    Denial risk: {readiness.overall_denial_risk}
                  </span>
                </div>
              </div>

              {activeTab === 'evidence' && (
                <div className="tab-content">
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

              {activeTab === 'form' && (
                <div className="tab-content">
                  <PriorAuthFormDraft
                    hasClarification={hasClarification}
                    onSourceClick={handleSourceClick}
                  />
                </div>
              )}

              {activeTab === 'disclosure' && (
                <div className="tab-content">
                  <DisclosurePanel onSourceClick={handleSourceClick} />
                </div>
              )}

              {activeTab === 'agents' && (
                <div className="tab-content">
                  <AgentTimeline
                    hasRunAnalysis={hasRunAnalysis}
                    hasClarification={hasClarification}
                  />
                </div>
              )}
            </div>
          )}

          {!hasRunAnalysis && (
            <div className="idle-prompt">
              <div className="idle-prompt-inner">
                <div className="idle-icon">⚡</div>
                <div className="idle-title">AuthLens is ready</div>
                <div className="idle-sub">
                  An MRI Lumbar Spine order has been placed that may require prior authorization
                  from Meridian Health Plans (fictional), policy MHP-IMG-2201. Click{' '}
                  <strong>Check Readiness</strong> in the AuthLens panel to analyze this encounter.
                </div>
                <div className="idle-synthetic-note">
                  SYNTHETIC DATA — Jordan Rivera is a fictional patient created for the AuthLens
                  hackathon demo.
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {selectedSource && (
        <SourceDrawer
          sourceId={selectedSource.sourceId}
          excerpt={selectedSource.excerpt}
          onClose={closeDrawer}
        />
      )}
    </div>
  );
}
