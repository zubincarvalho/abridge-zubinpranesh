import './AgentTimeline.css';
import { AGENT_STEPS } from '../data/mockCase';

type Props = {
  hasRunAnalysis: boolean;
};

const STATUS_LABEL: Record<string, string> = {
  completed: 'Completed',
  warning: 'Gaps found',
  review: 'Review required',
};

const STATUS_CLS: Record<string, string> = {
  completed: 'agent-chip-completed',
  warning: 'agent-chip-warning',
  review: 'agent-chip-review',
};

export default function AgentTimeline({ hasRunAnalysis }: Props) {
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
        {AGENT_STEPS.map((step, i) => (
          <div
            key={step.id}
            className={`agent-step ${hasRunAnalysis ? `agent-step--active animate-fade-in` : 'agent-step--idle'}`}
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className={`agent-step-icon ${hasRunAnalysis ? `icon-${step.status}` : 'icon-idle'}`}>
              {hasRunAnalysis ? step.icon : '○'}
            </div>
            {i < AGENT_STEPS.length - 1 && (
              <div className={`agent-connector ${hasRunAnalysis ? 'connector-active' : ''}`} />
            )}
            <div className="agent-step-content">
              <div className="agent-step-label">{step.label}</div>
              <div className="agent-step-detail">{hasRunAnalysis ? step.detail : 'Waiting...'}</div>
              {hasRunAnalysis && (
                <span className={`agent-chip ${STATUS_CLS[step.status]}`}>
                  {STATUS_LABEL[step.status]}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
