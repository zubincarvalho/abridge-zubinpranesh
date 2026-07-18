import './EvidenceMatrix.css';
import { EVIDENCE_ROWS } from '../data/mockCase';
import type { SourceDetail } from '../data/mockCase';

type Props = {
  hasClarification: boolean;
  onSourceClick: (source: SourceDetail) => void;
};

const STATUS_LABEL: Record<string, string> = { met: 'Met', weak: 'Weak', missing: 'Missing' };
const STATUS_CLS: Record<string, string> = { met: 'chip-met', weak: 'chip-weak', missing: 'chip-missing' };

export default function EvidenceMatrix({ hasClarification, onSourceClick }: Props) {
  const beforeScore = 58;
  const afterScore = 94;

  return (
    <div className="evidence-matrix panel">
      <div className="panel-header">
        <div className="matrix-header-left">
          <span className="panel-header-title">Authorization Readiness</span>
          <span className="matrix-policy-ref">BlueCross PPO · Lumbar Spine MRI Policy 2024-L07</span>
        </div>
        <div className="matrix-scores">
          <div className="matrix-score-item">
            <span className="matrix-score-label">Before clarification</span>
            <span className="matrix-score-value matrix-score-before">{beforeScore}%</span>
          </div>
          <div className="matrix-score-arrow">→</div>
          <div className="matrix-score-item">
            <span className="matrix-score-label">After clarification</span>
            <span className={`matrix-score-value ${hasClarification ? 'matrix-score-after' : 'matrix-score-after-dim'}`}>
              {afterScore}%
            </span>
          </div>
        </div>
      </div>

      <div className="matrix-table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>Criterion</th>
              <th>Status</th>
              <th>Evidence</th>
              <th>Source</th>
              <th>Suggested Fix</th>
            </tr>
          </thead>
          <tbody>
            {EVIDENCE_ROWS.map((row) => {
              const status = hasClarification ? row.statusAfter : row.status;
              const evidence = hasClarification ? row.evidenceAfter : row.evidence;
              return (
                <tr key={row.id} className={`matrix-row matrix-row--${status}`}>
                  <td className="matrix-criterion">{row.criterion}</td>
                  <td>
                    <span className={`chip ${STATUS_CLS[status]}`}>{STATUS_LABEL[status]}</span>
                  </td>
                  <td>
                    <button
                      className="matrix-evidence-link"
                      onClick={() => onSourceClick(row.sourceDetail)}
                    >
                      {evidence}
                    </button>
                  </td>
                  <td>
                    <button
                      className="matrix-source-link"
                      onClick={() => onSourceClick(row.sourceDetail)}
                    >
                      {row.source}
                      <span className="matrix-link-icon">↗</span>
                    </button>
                  </td>
                  <td className="matrix-fix">
                    {status === 'met' ? (
                      <span className="matrix-fix-none">—</span>
                    ) : (
                      <span className="matrix-fix-text">{row.suggestedFix}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
