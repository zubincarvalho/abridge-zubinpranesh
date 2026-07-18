import { useEffect } from 'react';
import './SourceDrawer.css';
import type { SourceDetail } from '../data/mockCase';

type Props = {
  source: SourceDetail;
  onClose: () => void;
};

const TYPE_LABELS: Record<SourceDetail['type'], { label: string; cls: string }> = {
  note: { label: 'Encounter Note', cls: 'chip-blue' },
  transcript: { label: 'Transcript', cls: 'chip-purple' },
  fhir: { label: 'FHIR Resource', cls: 'chip-teal' },
  clarification: { label: 'Clinician Clarification', cls: 'chip-met' },
};

const CONFIDENCE_MAP: Record<SourceDetail['type'], string> = {
  note: 'High',
  transcript: 'High',
  fhir: 'Structured',
  clarification: 'Verified',
};

export default function SourceDrawer({ source, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const meta = TYPE_LABELS[source.type];
  const confidence = CONFIDENCE_MAP[source.type];

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="source-drawer animate-slide-right">
        <div className="drawer-header">
          <div className="drawer-title-row">
            <span className="drawer-icon">🔗</span>
            <div>
              <div className="drawer-title">Linked Evidence</div>
              <div className="drawer-subtitle">Abridge Source Attribution</div>
            </div>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>

        <div className="drawer-body">
          <div className="drawer-meta-row">
            <span className={`chip ${meta.cls}`}>{meta.label}</span>
            {source.resourceType && (
              <span className="fhir-tag">{source.resourceType}</span>
            )}
          </div>

          <div className="drawer-section-title">{source.title}</div>

          {source.speaker && (
            <div className="drawer-speaker">
              <span className="section-label">Speaker</span>
              <span className="speaker-value">{source.speaker}</span>
            </div>
          )}

          <div className="drawer-excerpt-label">
            <span className="section-label">Excerpt</span>
          </div>
          <div className="drawer-excerpt">
            {source.excerpt.split('\n').map((line, i) => (
              <span key={i}>
                {line}
                {i < source.excerpt.split('\n').length - 1 && <br />}
              </span>
            ))}
          </div>

          <div className="drawer-confidence">
            <span className="section-label">Confidence</span>
            <span className={`chip ${confidence === 'High' || confidence === 'Verified' ? 'chip-met' : 'chip-blue'}`}>
              {confidence}
            </span>
          </div>

          <div className="drawer-note">
            <span className="drawer-note-icon">ℹ</span>
            Evidence extracted by Abridge AI from the encounter transcript and structured FHIR data.
          </div>
        </div>
      </aside>
    </>
  );
}
