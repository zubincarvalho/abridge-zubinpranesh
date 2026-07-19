import { useEffect, useState, type ReactNode } from 'react';
import './AgentTimeline.css';
import { EVENTS_PRE_CLARIFICATION, EVENTS_POST_CLARIFICATION } from '../data/mockCase';
import type { AgentStage, EventStatus } from '../data/mockCase';
import type { ApiAgentEvent, ApiCase } from '../api/client';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  events?: ApiAgentEvent[];
  /** When true, play the live "agents running" progression instead of the
   *  finished timeline (the API returns all events at once, so this is a
   *  client-driven walk through the analysis stages for the demo). */
  running?: boolean;
  /** The completed case — used to render per-agent proof-of-completion. */
  caseData?: ApiCase;
  onSourceClick?: (sourceId: string, excerpt?: string) => void;
};

function trunc(s: string, n = 96): string {
  return s.length > n ? s.slice(0, n) + '…' : s;
}

// A concrete artifact proving what an agent produced, built from real case
// data so judges can follow exactly what each step did.
function renderProof(
  stage: AgentStage,
  c: ApiCase | undefined,
  onSourceClick?: (sourceId: string, excerpt?: string) => void,
) {
  if (!c) return null;
  const allEvidence = c.assessments.flatMap((a) => a.evidence);

  switch (stage) {
    case 'intake':
      return (
        <ProofBox label="Loaded">
          {c.patient.chart_items.length} chart items · encounter note · ambient transcript
        </ProofBox>
      );
    case 'policy_parsing':
      if (!c.criteria.length) return null;
      return (
        <ProofBox label={`Parsed ${c.criteria.length} criteria from ${c.policy.policy_id}`}>
          <div className="proof-chips">
            {c.criteria.map((cr) => (
              <span key={cr.criterion_id} className="proof-chip" title={cr.label}>{cr.criterion_id}</span>
            ))}
          </div>
        </ProofBox>
      );
    case 'evidence_retrieval':
    case 'evidence_mapping': {
      if (!allEvidence.length) return null;
      const ex = allEvidence[0];
      return (
        <ProofBox label={`${allEvidence.length} verbatim excerpt(s) cited across ${c.criteria.length} criteria`}>
          {ex && (
            <button
              className="proof-quote"
              onClick={() => onSourceClick?.(ex.source_id, ex.excerpt)}
              title="Open cited source"
            >
              “{trunc(ex.excerpt)}” <span className="proof-quote-arrow">↗</span>
            </button>
          )}
        </ProofBox>
      );
    }
    case 'gap_detection': {
      if (!c.assessments.length) return null;
      const tally: Record<string, number> = {};
      for (const a of c.assessments) tally[a.status] = (tally[a.status] ?? 0) + 1;
      const score = c.readiness_history.at(-1)?.score;
      const questions = c.clarification_questions.length;
      return (
        <ProofBox label="Assessed all criteria">
          <div className="proof-pills">
            {tally.met ? <span className="proof-pill proof-pill--met">{tally.met} supported</span> : null}
            {tally.weak ? <span className="proof-pill proof-pill--weak">{tally.weak} weak</span> : null}
            {tally.conflicting ? <span className="proof-pill proof-pill--weak">{tally.conflicting} conflicting</span> : null}
            {tally.missing ? <span className="proof-pill proof-pill--missing">{tally.missing} not documented</span> : null}
            {score != null && <span className="proof-pill proof-pill--score">Readiness {score}/100</span>}
          </div>
          {questions > 0 && (
            <div className="proof-sub">{questions} clarification question{questions > 1 ? 's' : ''} raised</div>
          )}
        </ProofBox>
      );
    }
    case 'clarification': {
      const clar = c.clarifications[0];
      if (clar) return <ProofBox label="Recorded verbatim">“{trunc(clar.response)}”</ProofBox>;
      const oq = c.clarification_questions.find((q) => q.status === 'open');
      return oq ? <ProofBox label="Question to clinician">{trunc(oq.question)}</ProofBox> : null;
    }
    case 'disclosure_review': {
      if (!c.disclosure_decisions.length) return null;
      const inc = c.disclosure_decisions.filter((d) => d.decision === 'include').length;
      const exc = c.disclosure_decisions.filter((d) => d.decision === 'exclude').length;
      return (
        <ProofBox label="Minimum-necessary review">
          {inc} source(s) included · {exc} withheld
        </ProofBox>
      );
    }
    case 'packet_generation':
      return c.packet ? (
        <ProofBox label="Packet drafted">
          {c.packet.claims.length} cited claims · {c.packet.sections.length} sections
        </ProofBox>
      ) : null;
    case 'verification':
      return c.verification ? (
        <ProofBox label="Independent verification" tone={c.verification.passed ? 'ok' : 'bad'}>
          {c.verification.passed
            ? `Passed · ${c.verification.checked_claim_count} claims checked · 0 blocking issues`
            : `${c.verification.issues.length} blocking issue(s)`}
        </ProofBox>
      ) : null;
    case 'form_drafting':
      return c.form_draft ? (
        <ProofBox label="Mock form">{c.form_draft.fields.length} fields populated · ready for review</ProofBox>
      ) : null;
    case 'human_review':
      return <ProofBox label="Terminal">Clinician review required — nothing is submitted</ProofBox>;
    default:
      return null;
  }
}

function ProofBox({ label, tone, children }: { label: string; tone?: 'ok' | 'bad'; children: ReactNode }) {
  return (
    <div className={`agent-proof${tone ? ` agent-proof--${tone}` : ''}`}>
      <div className="agent-proof-label">
        <span className="agent-proof-check">✓</span> {label}
      </div>
      <div className="agent-proof-body">{children}</div>
    </div>
  );
}

// The agents that run during the analysis pass, in execution order. Used to
// animate the live progression while `runAnalysis` is in flight.
const RUN_SEQUENCE: { stage: AgentStage; agent: string; note: string }[] = [
  { stage: 'intake', agent: 'Intake', note: 'Validating encounter inputs' },
  { stage: 'policy_parsing', agent: 'Policy Agent', note: 'Parsing MHP-IMG-2201 into discrete criteria' },
  { stage: 'evidence_retrieval', agent: 'Evidence Retrieval Agent', note: 'Searching note, transcript & FHIR chart per criterion' },
  { stage: 'evidence_mapping', agent: 'Evidence Mapper Agent', note: 'Verifying verbatim citations against sources' },
  { stage: 'gap_detection', agent: 'Gap & Readiness Agent', note: 'Classifying criteria and scoring documentation readiness' },
];
const RUN_STEP_MS = 850;

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

export default function AgentTimeline({ hasRunAnalysis, hasClarification, events: liveEvents, running, caseData, onSourceClick }: Props) {
  // Live progression: walk the run sequence one agent at a time, holding on
  // the current agent until the real analysis result arrives (running=false).
  const [activeIdx, setActiveIdx] = useState(0);
  useEffect(() => {
    if (!running) return;
    setActiveIdx(0);
    const id = setInterval(() => {
      setActiveIdx((i) => Math.min(i + 1, RUN_SEQUENCE.length - 1));
    }, RUN_STEP_MS);
    return () => clearInterval(id);
  }, [running]);

  // Fallback simulated progression: only shown while running AND no real
  // streamed events have arrived yet (e.g. the backend can't stream).
  if (running && !(liveEvents && liveEvents.length)) {
    return (
      <div className="agent-timeline panel">
        <div className="panel-header">
          <span className="panel-header-title">AuthLens Agent Workflow</span>
          <span className="chip chip-running">
            <span className="agent-run-dot" /> Agents running…
          </span>
        </div>
        <div className="agent-timeline-body">
          {RUN_SEQUENCE.map((s, i) => {
            const status: EventStatus | 'pending' =
              i < activeIdx ? 'completed' : i === activeIdx ? 'started' : 'pending';
            return (
              <div
                key={s.stage}
                className={`agent-step agent-step--active agent-step--${status}`}
              >
                <div className={`agent-step-icon icon-${status === 'pending' ? 'idle' : status}`}>
                  {status === 'started' ? (
                    <span className="agent-spinner" aria-label="running" />
                  ) : status === 'completed' ? (
                    <span className="agent-step-num">✓</span>
                  ) : (
                    <span className="agent-step-num">{i + 1}</span>
                  )}
                  <span className="agent-step-emoji">{STAGE_ICON[s.stage]}</span>
                </div>
                {i < RUN_SEQUENCE.length - 1 && <div className="agent-connector connector-active" />}
                <div className="agent-step-content">
                  <div className="agent-step-label">{s.agent}</div>
                  <div className="agent-step-detail">{s.note}</div>
                  <div className="agent-step-meta">
                    <span className={`agent-chip ${STATUS_CLS[status === 'pending' ? 'skipped' : status]}`}>
                      {status === 'completed' ? 'Completed' : status === 'started' ? 'Working…' : 'Queued'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  const rawEvents: TimelineEvt[] = (liveEvents as TimelineEvt[] | undefined)
    ?? (hasClarification ? EVENTS_POST_CLARIFICATION : EVENTS_PRE_CLARIFICATION);
  const steps = toSteps(rawEvents);
  const doneCount = steps.filter((s) => s.status === 'completed').length;

  return (
    <div className="agent-timeline panel">
      <div className="panel-header">
        <span className="panel-header-title">AuthLens Agent Workflow</span>
        {running ? (
          <span className="chip chip-running"><span className="agent-run-dot" /> Agents running…</span>
        ) : hasRunAnalysis ? (
          <span className="chip chip-met">{doneCount} agents completed</span>
        ) : (
          <span className="chip chip-gray">Idle</span>
        )}
      </div>
      <div className="agent-timeline-body">
        {!hasRunAnalysis && !running ? (
          <div className="agent-idle-msg">
            Run analysis to see each agent complete in order.
          </div>
        ) : (
          steps.map((step, i) => {
            const proof = step.status === 'completed'
              ? renderProof(step.stage, caseData, onSourceClick)
              : null;
            return (
              <div
                key={step.key}
                className={`agent-step agent-step--active animate-fade-in agent-step--${step.status}`}
                style={{ animationDelay: `${i * 130}ms` }}
              >
                <div className={`agent-step-icon icon-${step.status}`}>
                  {step.status === 'started' ? (
                    <span className="agent-spinner" aria-label="running" />
                  ) : (
                    <span className="agent-step-num">{step.status === 'completed' ? '✓' : i + 1}</span>
                  )}
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
                  {proof}
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
            );
          })
        )}
      </div>
    </div>
  );
}
