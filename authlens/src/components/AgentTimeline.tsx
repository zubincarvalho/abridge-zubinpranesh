import './AgentTimeline.css';
import { EVENTS_PRE_CLARIFICATION, EVENTS_POST_CLARIFICATION } from '../data/mockCase';
import type { AgentStage, EventStatus } from '../data/mockCase';
import type { ApiAgentEvent } from '../api/client';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  events?: ApiAgentEvent[];
};

const STAGE_ICON: Record<AgentStage, string> = {
  intake: '📥',
  policy_parsing: '📋',
  evidence_retrieval: '🔍',
  evidence_mapping: '🗺',
  gap_detection: '⚠',
  clarification: '💬',
  disclosure_review: '🔒',
  packet_generation: '📦',
  verification: '✔',
  form_drafting: '📝',
  human_review: '👁',
};

const STATUS_CLS: Record<EventStatus, string> = {
  completed: 'agent-chip-completed',
  started: 'agent-chip-started',
  failed: 'agent-chip-failed',
  skipped: 'agent-chip-skipped',
};

const STATUS_LABEL: Record<EventStatus, string> = {
  completed: 'Completed',
  started: 'In progress',
  failed: 'Failed',
  skipped: 'Skipped',
};

export default function AgentTimeline({ hasRunAnalysis, hasClarification, events: liveEvents }: Props) {
  // Use live events if available, sorted by sequence; fall back to mock constants
  const events = liveEvents
    ? [...liveEvents].sort((a, b) => a.sequence - b.sequence)
    : (hasClarification ? EVENTS_POST_CLARIFICATION : EVENTS_PRE_CLARIFICATION);

  return (
    <div className="agent-timeline panel">
      <div className="panel-header">
        <span className="panel-header-title">AuthLens Agent Workflow</span>
        {hasRunAnalysis ? (
          <span className="chip chip-met">Run complete</span>
        ) : (
          <span className="chip chip-gray">Idle</span>
        )}
      </div>
      <div className="agent-timeline-body">
        {!hasRunAnalysis ? (
          <div className="agent-idle-msg">
            Run analysis to see the agent pipeline.
          </div>
        ) : (
          events.map((evt, i) => (
            <div
              key={evt.event_id}
              className="agent-step agent-step--active animate-fade-in"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className={`agent-step-icon icon-${evt.status}`}>
                {STAGE_ICON[evt.stage]}
              </div>
              {i < events.length - 1 && (
                <div className="agent-connector connector-active" />
              )}
              <div className="agent-step-content">
                <div className="agent-step-label">{evt.title}</div>
                {evt.detail && (
                  <div className="agent-step-detail">{evt.detail}</div>
                )}
                {evt.related_ids.length > 0 && (
                  <div className="agent-step-ids">
                    {evt.related_ids.map((id) => (
                      <span key={id} className="agent-id-tag">{id}</span>
                    ))}
                  </div>
                )}
                <div className="agent-step-meta">
                  <span className={`agent-chip ${STATUS_CLS[evt.status]}`}>
                    {STATUS_LABEL[evt.status]}
                  </span>
                  <span className="agent-step-time">
                    {evt.occurred_at.replace('T', ' ').replace('Z', ' UTC')}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
