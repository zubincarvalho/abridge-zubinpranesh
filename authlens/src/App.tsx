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
import SourceDrawer from './components/SourceDrawer';
import type { SourceDetail } from './data/mockCase';

type TabKey = 'evidence' | 'form' | 'agents';

export default function App() {
  const [hasRunAnalysis, setHasRunAnalysis] = useState(false);
  const [hasClarification, setHasClarification] = useState(false);
  const [selectedSource, setSelectedSource] = useState<SourceDetail | undefined>();
  const [activeTab, setActiveTab] = useState<TabKey>('evidence');

  function handleCheckReadiness() {
    setHasRunAnalysis(true);
    setActiveTab('evidence');
  }

  function handleAddClarification() {
    setHasClarification(true);
  }

  function handleSourceClick(source: SourceDetail) {
    setSelectedSource(source);
  }

  function closeDrawer() {
    setSelectedSource(undefined);
  }

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
                  {(['evidence', 'form', 'agents'] as TabKey[]).map((tab) => (
                    <button
                      key={tab}
                      className={`tab-btn ${activeTab === tab ? 'tab-btn--active' : ''}`}
                      onClick={() => setActiveTab(tab)}
                    >
                      {tab === 'evidence' && '📊 Evidence Matrix'}
                      {tab === 'form' && '📋 Prior Auth Form'}
                      {tab === 'agents' && '⚡ Agent Log'}
                    </button>
                  ))}
                </div>
                <div className="tab-bar-meta">
                  {hasClarification ? (
                    <span className="chip chip-met">Readiness: 94%</span>
                  ) : (
                    <span className="chip chip-orange">Readiness: 58%</span>
                  )}
                </div>
              </div>

              {activeTab === 'evidence' && (
                <div className="tab-content">
                  <EvidenceMatrix hasClarification={hasClarification} onSourceClick={handleSourceClick} />
                  <GapResolutionPanel hasClarification={hasClarification} onAddClarification={handleAddClarification} />
                </div>
              )}

              {activeTab === 'form' && (
                <div className="tab-content">
                  <PriorAuthFormDraft hasClarification={hasClarification} onSourceClick={handleSourceClick} />
                </div>
              )}

              {activeTab === 'agents' && (
                <div className="tab-content">
                  <AgentTimeline hasRunAnalysis={hasRunAnalysis} />
                  <div className="agent-log-note panel">
                    <div className="panel-body">
                      <div className="section-label" style={{ marginBottom: '6px' }}>Agent Run Details</div>
                      <div className="agent-log-entries">
                        <div className="log-entry log-entry--ok">
                          <span className="log-ts">07/18/26 14:02:01</span>
                          <span className="log-agent">Policy Agent</span>
                          <span className="log-msg">Fetched BlueCross PPO Lumbar Spine MRI policy 2024-L07. Parsed 5 criteria.</span>
                        </div>
                        <div className="log-entry log-entry--ok">
                          <span className="log-ts">07/18/26 14:02:02</span>
                          <span className="log-agent">Evidence Agent</span>
                          <span className="log-msg">Scanned Abridge note (4 sections). Loaded FHIR resources: Condition×2, MedicationRequest×1, ServiceRequest×2.</span>
                        </div>
                        <div className="log-entry log-entry--warn">
                          <span className="log-ts">07/18/26 14:02:03</span>
                          <span className="log-agent">Gap Agent</span>
                          <span className="log-msg">Criteria met: 2/5. Weak: 2/5. Missing: 1/5. Generated 3 follow-up questions.</span>
                        </div>
                        <div className="log-entry log-entry--ok">
                          <span className="log-ts">07/18/26 14:02:04</span>
                          <span className="log-agent">Disclosure Agent</span>
                          <span className="log-msg">Filtered hypertension history and preventive-care details as unrelated to PA request.</span>
                        </div>
                        <div className="log-entry log-entry--review">
                          <span className="log-ts">07/18/26 14:02:05</span>
                          <span className="log-agent">Form Agent</span>
                          <span className="log-msg">Drafted prior-auth request. Status: Needs clarification. Awaiting clinician input.</span>
                        </div>
                        {hasClarification && (
                          <div className="log-entry log-entry--ok animate-fade-in">
                            <span className="log-ts">07/18/26 14:06:14</span>
                            <span className="log-agent">Form Agent</span>
                            <span className="log-msg">Clinician clarification received. Readiness updated: 94%. Status: Ready for human review.</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
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
                  An MRI Lumbar Spine order has been placed that may require prior authorization.
                  Click <strong>Check Readiness</strong> in the AuthLens panel to analyze this encounter.
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {selectedSource && (
        <SourceDrawer source={selectedSource} onClose={closeDrawer} />
      )}
    </div>
  );
}
