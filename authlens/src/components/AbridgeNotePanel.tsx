import './AbridgeNotePanel.css';
import { NOTE_TEXT, NOTE_HIGHLIGHTS, CLARIFICATION_RESPONSE } from '../data/mockCase';
import type { NoteHighlight } from '../data/mockCase';
import type { ApiCriterionAssessment, ApiPolicyCriterion } from '../api/client';

type Props = {
  hasClarification: boolean;
  onPhraseClick: (sourceId: string, excerpt?: string) => void;
  noteText?: string;
  noteSourceId?: string;
  transcriptText?: string;
  transcriptSourceId?: string;
  assessments?: ApiCriterionAssessment[];
  criteria?: ApiPolicyCriterion[];
};

type Segment = { text: string; highlight?: NoteHighlight };

function buildSegments(text: string, globalOffset: number, highlights: NoteHighlight[]): Segment[] {
  const relevant = highlights
    .filter((h) => h.start < globalOffset + text.length && h.end > globalOffset)
    .map((h) => ({
      ...h,
      localStart: Math.max(0, h.start - globalOffset),
      localEnd: Math.min(text.length, h.end - globalOffset),
    }))
    .sort((a, b) => a.localStart - b.localStart);

  const segments: Segment[] = [];
  let cursor = 0;

  for (const h of relevant) {
    if (h.localStart > cursor) {
      segments.push({ text: text.slice(cursor, h.localStart) });
    }
    segments.push({ text: text.slice(h.localStart, h.localEnd), highlight: h });
    cursor = h.localEnd;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) });
  }

  return segments;
}

function deriveHighlights(
  assessments: ApiCriterionAssessment[],
  criteria: ApiPolicyCriterion[],
  noteSourceId: string,
): NoteHighlight[] {
  const labelMap = Object.fromEntries(criteria.map((c) => [c.criterion_id, c.label]));
  const highlights: NoteHighlight[] = [];
  for (const a of assessments) {
    for (const ev of a.evidence) {
      if (ev.source_id === noteSourceId && ev.span) {
        highlights.push({
          id: ev.evidence_id,
          start: ev.span.start,
          end: ev.span.end,
          criterionId: a.criterion_id,
          sourceId: ev.source_id,
          label: `${a.criterion_id}: ${labelMap[a.criterion_id] ?? a.criterion_id}`,
        });
      }
    }
  }
  return highlights.sort((a, b) => a.start - b.start);
}

function Noteparagraph({
  text,
  globalOffset,
  highlights,
  onPhraseClick,
}: {
  text: string;
  globalOffset: number;
  highlights: NoteHighlight[];
  onPhraseClick: (sourceId: string, excerpt?: string) => void;
}) {
  const segments = buildSegments(text, globalOffset, highlights);

  return (
    <p className="note-text">
      {segments.map((seg, i) =>
        seg.highlight ? (
          <button
            key={i}
            className={`note-highlight note-highlight--${seg.highlight.criterionId.toLowerCase()}`}
            onClick={() => onPhraseClick(seg.highlight!.sourceId, seg.text)}
            title={seg.highlight.label}
          >
            {seg.text}
            <span className="note-highlight-indicator" aria-hidden>
              {seg.highlight.criterionId}
            </span>
          </button>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </p>
  );
}

function renderTranscript(text: string) {
  // Ambient transcript is speaker-turn text; render each turn on its own line.
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, i) => {
      const m = line.match(/^([A-Za-z .]+):\s*(.*)$/);
      return (
        <p className="transcript-turn" key={i}>
          {m ? (
            <>
              <span className="transcript-speaker">{m[1]}:</span> {m[2]}
            </>
          ) : (
            line
          )}
        </p>
      );
    });
}

export default function AbridgeNotePanel({ hasClarification, onPhraseClick, noteText, noteSourceId, transcriptText, transcriptSourceId, assessments, criteria }: Props) {
  const activeNoteText = noteText ?? NOTE_TEXT;

  // Derive highlights from live assessments when available
  const highlights =
    assessments && criteria && noteSourceId
      ? deriveHighlights(assessments, criteria, noteSourceId)
      : NOTE_HIGHLIGHTS;

  // Find recorded clarification from live data
  const clarificationText = hasClarification
    ? (assessments?.flatMap((a) => a.evidence).find(
        (ev) => ev.source_type === 'clinician_clarification'
      )?.excerpt ?? CLARIFICATION_RESPONSE)
    : null;

  const paragraphs = activeNoteText.split('\n\n');
  let offset = 0;

  return (
    <div className="abridge-panel panel">
      <div className="panel-header">
        <div className="abridge-header-left">
          <div className="abridge-logo">
            <span className="abridge-logo-a">A</span>
            <span className="abridge-logo-text">bridge</span>
          </div>
          <div>
            <div className="abridge-title">Ambient Clinical Documentation</div>
            <div className="abridge-subtitle">Abridge AI Scribe · 07/18/2026 · SYNTHETIC</div>
          </div>
        </div>
        <div className="abridge-header-chips">
          <span className="chip chip-purple">Ambient AI Scribe</span>
          <span className="chip chip-blue">Analysis basis</span>
        </div>
      </div>

      <div className="note-body">
        <div className="abridge-basis-banner">
          This is the <strong>complete encounter documentation</strong> captured by the Abridge
          ambient scribe — the clinical note and the ambient transcript below are the sole basis
          for AuthLens's readiness analysis. Every cited excerpt is verbatim from this text.
        </div>

        <div className="note-doc-section">
          <div className="note-doc-heading">
            <span className="note-doc-title">Clinical Note</span>
            <span className="note-doc-src">source: {noteSourceId ?? 'note-001'}</span>
          </div>
          <div className="note-highlight-legend">
            <span className="legend-label">Highlighted =</span>
            <span className="legend-item legend-item--criteria">evidence cited by AuthLens</span>
            <span className="legend-sep">·</span>
            <span className="legend-hint">click to view source</span>
          </div>

        {paragraphs.map((para, i) => {
          const go = offset;
          offset += para.length + 2; // +2 for '\n\n'
          return (
            <Noteparagraph
              key={i}
              text={para}
              globalOffset={go}
              highlights={highlights}
              onPhraseClick={onPhraseClick}
            />
          );
        })}
        </div>

        {transcriptText && (
          <div className="note-doc-section note-doc-section--transcript">
            <div className="note-doc-heading">
              <span className="note-doc-title">Ambient Encounter Transcript</span>
              <span className="note-doc-src">source: {transcriptSourceId ?? 'transcript-001'}</span>
            </div>
            <div className="transcript-body">{renderTranscript(transcriptText)}</div>
          </div>
        )}

        {hasClarification && clarificationText && (
          <section className="note-section note-section--clarification animate-fade-in">
            <div className="note-section-label">
              <span className="clarification-badge">Clinician Clarification Added</span>
            </div>
            <p className="note-text note-clarification-text">{clarificationText}</p>
          </section>
        )}

        <div className="note-footer">
          <span className="note-footer-item">Generated by Abridge AI</span>
          <span className="note-footer-sep">·</span>
          <span className="note-footer-item">Requires clinician attestation</span>
          <span className="note-footer-sep">·</span>
          <span className="note-footer-item highlight-hint">
            Highlighted phrases = evidence cited by AuthLens
          </span>
        </div>
      </div>
    </div>
  );
}
