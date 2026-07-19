import { useState, useCallback } from 'react';
import './index.css';
import './App.css';

import PatientBanner      from './components/PatientBanner';
import EHRNavigation      from './components/EHRNavigation';
import OrderContextPanel  from './components/OrderContextPanel';
import AbridgeNotePanel   from './components/AbridgeNotePanel';
import AgentTimeline      from './components/AgentTimeline';
import EvidenceMatrix     from './components/EvidenceMatrix';
import GapResolutionPanel from './components/GapResolutionPanel';
import PriorAuthFormDraft from './components/PriorAuthFormDraft';
import PacketStatusPanel  from './components/PacketStatusPanel';
import SourceDrawer       from './components/SourceDrawer';
import CasePicker         from './components/CasePicker';
import ReadinessGauge     from './components/ReadinessGauge';

import {
  runAnalysis,
  runAnalysisStreamed,
  submitClarification,
  generatePacket,
  verifyPacket,
  draftForm,
  hasRunAnalysis as apiHasRun,
  hasClarificationRecorded,
  openQuestion,
  type ApiCase,
  type ApiAgentEvent,
} from './api/client';

import { CLARIFICATION_RESPONSE } from './data/mockCase';

type CenterTab = 'evidence' | 'note' | 'agents';
type SelectedSource = { sourceId: string; excerpt?: string };
type NoteFocus = { sourceId: string; excerpt?: string; nonce: number };

export default function App() {
  const [liveCase,       setLiveCase]       = useState<ApiCase | null>(null);
  const [caseId,         setCaseId]         = useState<string | null>(null);
  const [isLoading,      setIsLoading]      = useState(false);
  const [loadingStage,   setLoadingStage]   = useState<string>('');
  const [apiError,       setApiError]       = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<SelectedSource | undefined>();
  const [centerTab,      setCenterTab]      = useState<CenterTab>('evidence');
  const [showFormDrawer, setShowFormDrawer] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [streamEvents, setStreamEvents] = useState<ApiAgentEvent[]>([]);
  const [showPicker, setShowPicker] = useState(true);
  const [noteFocus, setNoteFocus] = useState<NoteFocus | undefined>();

  // A case is chosen from the scenario picker (demo fixture or a real Abridge
  // encounter). Each selection is a fresh intake-stage case.
  const handleCaseSelected = useCallback((c: ApiCase) => {
    setLiveCase(c);
    setCaseId(c.case_id);
    setShowPicker(false);
    setStreamEvents([]);
    setSelectedSource(undefined);
    setNoteFocus(undefined);
    setShowFormDrawer(false);
    setApiError(null);
    setCenterTab('evidence');
  }, []);

  // Derived booleans from live case
  const hasRunAnalysis   = liveCase ? apiHasRun(liveCase)             : false;
  const hasClarification = liveCase ? hasClarificationRecorded(liveCase) : false;

  const handleCheckReadiness = useCallback(async () => {
    if (!caseId) {
      // No backend — instant mock transition
      setLiveCase(null);
      setCenterTab('evidence');
      return;
    }
    // Minimum time to keep the fallback simulated progression on screen when
    // the backend can't stream (so it's visible even in deterministic mode).
    const MIN_SHOW_MS = 4600;
    setIsLoading(true);
    setAnalysisRunning(true);
    setStreamEvents([]);
    setLoadingStage('Running analysis…');
    setApiError(null);
    const startedAt = performance.now();
    try {
      let updated: ApiCase;
      try {
        // Preferred path: stream each agent's completion live.
        updated = await runAnalysisStreamed(caseId, (ev) => {
          setStreamEvents((prev) => [...prev, ev]);
        });
      } catch {
        // Fallback: single call + simulated progression held for MIN_SHOW_MS.
        setStreamEvents([]);
        updated = await runAnalysis(caseId);
        const elapsed = performance.now() - startedAt;
        if (elapsed < MIN_SHOW_MS) {
          await new Promise((resolve) => setTimeout(resolve, MIN_SHOW_MS - elapsed));
        }
      }
      setLiveCase(updated);
      // Land on the Activity tab so judges see the completed agent trail with
      // each agent's proof-of-completion before moving to the evidence matrix.
      setCenterTab('agents');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setApiError(`Analysis failed: ${msg}`);
    } finally {
      setIsLoading(false);
      setAnalysisRunning(false);
      setLoadingStage('');
    }
  }, [caseId]);

  const handleAddClarification = useCallback(async () => {
    setCenterTab('evidence');

    if (!caseId || !liveCase) {
      // Offline fallback — instant mock transition
      setLiveCase(null);
      return;
    }

    const question = openQuestion(liveCase);
    if (!question) return;

    setIsLoading(true);
    setApiError(null);

    try {
      setLoadingStage('Recording clarification…');
      const afterClar = await submitClarification(caseId, question.question_id, CLARIFICATION_RESPONSE);
      setLiveCase(afterClar);

      setLoadingStage('Generating packet…');
      const afterPacket = await generatePacket(caseId);
      setLiveCase(afterPacket);

      setLoadingStage('Verifying packet…');
      const afterVerify = await verifyPacket(caseId);
      setLiveCase(afterVerify);

      setLoadingStage('Drafting form…');
      const afterForm = await draftForm(caseId);
      setLiveCase(afterForm);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setApiError(`Clarification pipeline failed: ${msg}`);
    } finally {
      setIsLoading(false);
      setLoadingStage('');
    }
  }, [caseId, liveCase]);

  function handleSourceClick(sourceId: string, excerpt?: string) {
    setSelectedSource({ sourceId, excerpt });
  }

  // Click-to-source: if the evidence is grounded in the encounter note, jump to
  // the Note View and pulse the exact verbatim span; otherwise open the source
  // drawer (chart items / clarifications aren't in the note body).
  function handleFocusSource(sourceId: string, excerpt?: string) {
    if (liveCase && sourceId === liveCase.encounter_note.source_id && excerpt) {
      setCenterTab('note');
      setNoteFocus({ sourceId, excerpt, nonce: Date.now() });
    } else {
      handleSourceClick(sourceId, excerpt);
    }
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
              Authorization Review
              <span className="pa-activity-model">AuthLens · Hackathon prototype using Abridge-provided synthetic data</span>
            </div>
            <div className="pa-activity-meta">
              <span className="chip chip-gray">MHP-IMG-2201</span>
              <span className="chip chip-gray">CPT 72148</span>
              <span className="pa-synthetic-tag">SYNTHETIC DATA</span>
              <button className="pa-switch-case" onClick={() => setShowPicker(true)}>
                ⇄ Switch case
              </button>
            </div>
          </div>

          {/* Loading / error banner */}
          {isLoading && (
            <div className="pa-loading-banner">
              <span className="pa-loading-spinner" />
              {loadingStage || 'Working…'}
            </div>
          )}
          {apiError && (
            <div className="pa-error-banner">
              ⚠ {apiError}
              <button className="pa-error-dismiss" onClick={() => setApiError(null)}>✕</button>
            </div>
          )}

          {/* 3-column PA workspace */}
          <div className="pa-workspace">

            {/* ── Left column ── */}
            <aside className="pa-col pa-col-left">
              <OrderContextPanel
                hasRunAnalysis={hasRunAnalysis}
                hasClarification={hasClarification}
                onCheckReadiness={handleCheckReadiness}
                onAddClarification={handleAddClarification}
                assessments={liveCase?.assessments}
                chartItems={liveCase?.patient.chart_items}
                isLoading={isLoading}
              />
            </aside>

            {/* ── Center column ── */}
            <section className="pa-col pa-col-center">
              {analysisRunning ? (
                <div className="pa-col-content animate-fade-in">
                  <AgentTimeline
                    hasRunAnalysis
                    hasClarification={false}
                    running
                    events={streamEvents.length ? streamEvents : undefined}
                    onSourceClick={handleSourceClick}
                  />
                </div>
              ) : hasRunAnalysis ? (
                <>
                  <div className="pa-col-tabs">
                    {(
                      [
                        { key: 'evidence', label: 'Evidence'  },
                        { key: 'note',     label: 'Note View' },
                        { key: 'agents',   label: 'Activity'  },
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
                          onFocusSource={handleFocusSource}
                          assessments={liveCase?.assessments}
                          criteria={liveCase?.criteria}
                          policy={liveCase?.policy}
                        />
                        <GapResolutionPanel
                          hasClarification={hasClarification}
                          onAddClarification={handleAddClarification}
                          question={liveCase ? openQuestion(liveCase) ?? undefined : undefined}
                          clarificationResponse={liveCase?.clarifications[0]?.response}
                        />
                      </div>
                    )}
                    {centerTab === 'note' && (
                      <div className="pa-col-content animate-fade-in">
                        <AbridgeNotePanel
                          hasClarification={hasClarification}
                          onPhraseClick={handleSourceClick}
                          noteText={liveCase?.encounter_note.text}
                          noteSourceId={liveCase?.encounter_note.source_id}
                          transcriptText={liveCase?.encounter_transcript?.text}
                          transcriptSourceId={liveCase?.encounter_transcript?.source_id}
                          assessments={liveCase?.assessments}
                          criteria={liveCase?.criteria}
                          focus={noteFocus}
                        />
                      </div>
                    )}
                    {centerTab === 'agents' && (
                      <div className="pa-col-content animate-fade-in">
                        <AgentTimeline
                          hasRunAnalysis={hasRunAnalysis}
                          hasClarification={hasClarification}
                          events={liveCase?.events}
                          caseData={liveCase ?? undefined}
                          onSourceClick={handleSourceClick}
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

            {/* ── Right column ── */}
            <aside className="pa-col pa-col-right">
              {hasRunAnalysis && liveCase && (
                <ReadinessGauge history={liveCase.readiness_history} />
              )}
              <PacketStatusPanel
                hasRunAnalysis={hasRunAnalysis}
                hasClarification={hasClarification}
                onOpenForm={() => setShowFormDrawer(true)}
                assessments={liveCase?.assessments}
                caseStatus={liveCase?.status}
              />
            </aside>
          </div>
        </main>
      </div>

      {selectedSource && (
        <SourceDrawer
          sourceId={selectedSource.sourceId}
          excerpt={selectedSource.excerpt}
          onClose={() => setSelectedSource(undefined)}
          caseId={caseId ?? undefined}
        />
      )}

      {showFormDrawer && (
        <div className="form-drawer-overlay" onClick={() => setShowFormDrawer(false)}>
          <div className="form-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="form-drawer-header">
              <span className="form-drawer-title">Authorization Form Draft</span>
              <button className="form-drawer-close" onClick={() => setShowFormDrawer(false)}>✕</button>
            </div>
            <div className="form-drawer-body">
              <PriorAuthFormDraft
                hasClarification={hasClarification}
                onSourceClick={handleSourceClick}
                caseData={liveCase ?? undefined}
                formDraft={liveCase?.form_draft ?? undefined}
                assessments={liveCase?.assessments}
              />
            </div>
          </div>
        </div>
      )}

      {showPicker && (
        <CasePicker
          onCaseSelected={handleCaseSelected}
          onClose={liveCase ? () => setShowPicker(false) : undefined}
        />
      )}
    </div>
  );
}
