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

// The agent behind each stage — the demo wants to read as a chronological
// list of individual agents completing their work.
const STAGE_AGENT: Record<AgentStage, string> = {
  intake: 'Intake',
  policy_parsing: 'Policy Agent',
  evidence_retrieval: 'Evidence Retrieval Agent',
  evidence_mapping: 'Evidence Mapper Agent',
  gap_detection: 'Gap & Readiness Agent',
  clarification: 'Clinician Clarification',
  disclosure_review: 'Disclosure Agent',
  packet_generation: 'Packet Agent',
  verification: 'Verification Agent',
  form_drafting: 'Form Agent',
  human_review: 'Human Review',
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

type TimelineEvt = {
  event_id: string;
  stage: AgentStage;
  status: EventStatus;
  title: string;
  detail: string | null;
  related_ids: string[];
  occurred_at: string;
};

type Step = {
  key: string;
  stage: AgentStage;
  agent: string;
  detail: string | null;
  status: EventStatus;
  time: string;
  related_ids: string[];
};

const AGENT_SUFFIX = / (started|completed|failed|skipped)$/i;

// Collapse the raw started/completed event pairs into one row per agent action,
// preserving chronological order. A "started" with no matching terminal event
// (e.g. the clarification pause, or the terminal human-review milestone) stays
// as its own in-progress/milestone row.
function toSteps(events: TimelineEvt[]): Step[] {
  const sorted = [...events].sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  const steps: Step[] = [];
  const openByStage: Record<string, number> = {};

  for (const evt of sorted) {
    const agent = STAGE_AGENT[evt.stage] ?? evt.title.replace(AGENT_SUFFIX, '');
    if (evt.status === 'started') {
      openByStage[evt.stage] = steps.length;
      steps.push({
        key: evt.event_id,
        stage: evt.stage,
        agent,
        detail: evt.detail,
        status: 'started',
        time: evt.occurred_at,
        related_ids: evt.related_ids,
      });
    } else {
      const idx = openByStage[evt.stage];
      if (idx != null && steps[idx]?.status === 'started') {
        steps[idx] = {
          ...steps[idx],
          status: evt.status,
          detail: evt.detail ?? steps[idx].detail,
          time: evt.occurred_at,
          related_ids: evt.related_ids.length ? evt.related_ids : steps[idx].related_ids,
        };
        delete openByStage[evt.stage];
      } else {
        steps.push({
          key: evt.event_id,
          stage: evt.stage,
          agent,
          detail: evt.detail,
          status: evt.status,
          time: evt.occurred_at,
          related_ids: evt.related_ids,
        });
      }
    }
  }
  return steps;
}

export default function AgentTimeline({ hasRunAnalysis, hasClarification, events: liveEvents }: Props) {
  const rawEvents: TimelineEvt[] = (liveEvents as TimelineEvt[] | undefined)
    ?? (hasClarification ? EVENTS_POST_CLARIFICATION : EVENTS_PRE_CLARIFICATION);
  const steps = toSteps(rawEvents);
  const doneCount = steps.filter((s) => s.status === 'completed').length;

  return (
    <div className="agent-timeline panel">
      <div className="panel-header">
        <span className="panel-header-title">AuthLens Agent Workflow</span>
        {hasRunAnalysis ? (
          <span className="chip chip-met">{doneCount} agents completed</span>
        ) : (
          <span className="chip chip-gray">Idle</span>
        )}
      </div>
      <div className="agent-timeline-body">
        {!hasRunAnalysis ? (
          <div className="agent-idle-msg">
            Run analysis to see each agent complete in order.
          </div>
        ) : (
          steps.map((step, i) => (
            <div
              key={step.key}
              className={`agent-step agent-step--active animate-fade-in agent-step--${step.status}`}
              style={{ animationDelay: `${i * 45}ms` }}
            >
              <div className={`agent-step-icon icon-${step.status}`}>
                <span className="agent-step-num">{i + 1}</span>
                <span className="agent-step-emoji">{STAGE_ICON[step.stage]}</span>
              </div>
              {i < steps.length - 1 && (
                <div className="agent-connector connector-active" />
              )}
              <div className="agent-step-content">
                <div className="agent-step-label">{step.agent}</div>
                {step.detail && (
                  <div className="agent-step-detail">{step.detail}</div>
                )}
                {step.related_ids.length > 0 && (
                  <div className="agent-step-ids">
                    {step.related_ids.map((id) => (
                      <span key={id} className="agent-id-tag">{id}</span>
                    ))}
                  </div>
                )}
                <div className="agent-step-meta">
                  <span className={`agent-chip ${STATUS_CLS[step.status]}`}>
                    {STATUS_LABEL[step.status]}
                  </span>
                  <span className="agent-step-time">
                    {step.time.replace('T', ' ').replace('Z', ' UTC')}
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
