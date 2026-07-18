import { useEffect, useState } from 'react';
import './SourceDrawer.css';
import { SOURCE_LOOKUP } from '../data/mockCase';
import { getEvidenceSource, type ApiEvidenceSource } from '../api/client';

type Props = {
  sourceId: string;
  excerpt?: string;
  onClose: () => void;
  caseId?: string;
};

const TYPE_META: Record<string, { label: string; cls: string }> = {
  encounter_note: { label: 'Encounter Note', cls: 'chip-blue' },
  encounter_transcript: { label: 'Transcript', cls: 'chip-purple' },
  fhir_resource: { label: 'FHIR Resource', cls: 'chip-teal' },
  clinician_clarification: { label: 'Clinician Clarification', cls: 'chip-met' },
  clarification: { label: 'Clinician Clarification', cls: 'chip-met' },
};

export default function SourceDrawer({ sourceId, excerpt, onClose, caseId }: Props) {
  const [liveSource, setLiveSource] = useState<ApiEvidenceSource | null>(null);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => {
    if (!caseId) return;
    setLiveSource(null);
    setFetchError(false);
    getEvidenceSource(caseId, sourceId)
      .then(setLiveSource)
      .catch(() => setFetchError(true));
  }, [caseId, sourceId]);

  // Resolve source: live API → mock fallback
  const mockSource = SOURCE_LOOKUP[sourceId];
  const source: { source_id: string; label?: string; title?: string; content: string; source_type: string } | null =
    liveSource
      ? { source_id: liveSource.source_id, label: liveSource.label, title: liveSource.label, content: liveSource.content, source_type: liveSource.source_type }
      : mockSource
        ? { source_id: mockSource.source_id, title: mockSource.title, content: mockSource.content, source_type: mockSource.source_type }
        : null;

  const isLoading = caseId && !liveSource && !fetchError && !mockSource;

  if (isLoading) {
    return (
      <>
        <div className="drawer-backdrop" onClick={onClose} />
        <aside className="source-drawer animate-slide-right">
          <div className="drawer-header">
            <div className="drawer-title-row">
              <span className="drawer-icon">🔗</span>
              <div className="drawer-title">Loading source…</div>
            </div>
            <button className="drawer-close" onClick={onClose}>✕</button>
          </div>
        </aside>
      </>
    );
  }

  if (!source) {
    return (
      <>
        <div className="drawer-backdrop" onClick={onClose} />
        <aside className="source-drawer animate-slide-right">
          <div className="drawer-header">
            <div className="drawer-title-row">
              <span className="drawer-icon">⚠</span>
              <div className="drawer-title">Source not found: {sourceId}</div>
            </div>
            <button className="drawer-close" onClick={onClose}>✕</button>
          </div>
        </aside>
      </>
    );
  }

  const meta = TYPE_META[source.source_type] ?? { label: source.source_type, cls: 'chip-gray' };
  const title = source.title ?? source.label ?? sourceId;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="source-drawer animate-slide-right">
        <div className="drawer-header">
          <div className="drawer-title-row">
            <span className="drawer-icon">🔗</span>
            <div>
              <div className="drawer-title">Linked Evidence</div>
              <div className="drawer-subtitle">AuthLens Source Attribution</div>
            </div>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>

        <div className="drawer-body">
          <div className="drawer-meta-row">
            <span className={`chip ${meta.cls}`}>{meta.label}</span>
            <span className="drawer-source-id">{sourceId}</span>
          </div>

          <div className="drawer-section-title">{title}</div>

          {excerpt && (
            <div className="drawer-excerpt-section">
              <div className="drawer-excerpt-label">
                <span className="section-label">Cited excerpt</span>
              </div>
              <div className="drawer-excerpt drawer-excerpt--highlighted">
                {excerpt}
              </div>
            </div>
          )}

          <div className="drawer-content-section">
            <div className="drawer-excerpt-label">
              <span className="section-label">Full source content</span>
            </div>
            <div className="drawer-content">
              {source.content.split('\n').map((line, i) => (
                <span key={i}>
                  {line}
                  {i < source.content.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
          </div>

          <div className="drawer-note">
            <span className="drawer-note-icon">ℹ</span>
            Evidence extracted by Abridge AI from the encounter and structured FHIR data.
            Spans are half-open character offsets [start, end) into the source text.
          </div>
        </div>
      </aside>
    </>
  );
}
