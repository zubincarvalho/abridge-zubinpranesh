import { useEffect, useRef, useState } from 'react';
import './ReadinessGauge.css';
import type { ApiReadinessSummary } from '../api/client';

type Props = { history: ApiReadinessSummary[] };

const R = 52;
const CIRC = 2 * Math.PI * R;

function tone(score: number): 'high' | 'mid' | 'low' {
  if (score >= 85) return 'high';
  if (score >= 70) return 'mid';
  return 'low';
}

export default function ReadinessGauge({ history }: Props) {
  const current = history.length ? history[history.length - 1].score : 0;
  const previous = history.length > 1 ? history[0].score : null;
  const latest = history.length ? history[history.length - 1] : null;

  // Tween the displayed number toward `current` whenever it changes.
  const [display, setDisplay] = useState(current);
  const fromRef = useRef(current);
  useEffect(() => {
    const from = fromRef.current;
    const to = current;
    if (from === to) {
      setDisplay(to);
      return;
    }
    const DURATION = 900;
    let raf = 0;
    let start = 0;
    const step = (t: number) => {
      if (!start) start = t;
      const p = Math.min(1, (t - start) / DURATION);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (p < 1) raf = requestAnimationFrame(step);
      else fromRef.current = to;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [current]);

  const t = tone(display);
  const offset = CIRC * (1 - display / 100);
  const delta = previous != null ? current - previous : null;

  return (
    <div className={`readiness-gauge readiness-gauge--${t}`}>
      <div className="rg-header">
        <span className="rg-title">Documentation Readiness</span>
      </div>
      <div className="rg-dial-wrap">
        <svg className="rg-dial" viewBox="0 0 120 120" width="128" height="128">
          <circle className="rg-track" cx="60" cy="60" r={R} />
          <circle
            className="rg-progress"
            cx="60"
            cy="60"
            r={R}
            style={{ strokeDasharray: CIRC, strokeDashoffset: offset }}
          />
        </svg>
        <div className="rg-center">
          <span className="rg-score">{display}</span>
          <span className="rg-outof">/ 100</span>
        </div>
      </div>

      {delta != null && delta !== 0 && (
        <div className="rg-delta">
          <span className="rg-delta-badge">{delta > 0 ? `+${delta}` : delta}</span>
          <span className="rg-delta-text">
            {previous} → {current} after clarification
          </span>
        </div>
      )}

      {latest && (
        <div className="rg-breakdown">
          {latest.criteria_met > 0 && (
            <span className="rg-pill rg-pill--met">{latest.criteria_met} supported</span>
          )}
          {latest.criteria_weak > 0 && (
            <span className="rg-pill rg-pill--weak">{latest.criteria_weak} weak</span>
          )}
          {latest.criteria_conflicting > 0 && (
            <span className="rg-pill rg-pill--weak">{latest.criteria_conflicting} conflicting</span>
          )}
          {latest.criteria_missing > 0 && (
            <span className="rg-pill rg-pill--missing">{latest.criteria_missing} missing</span>
          )}
        </div>
      )}

      <div className="rg-foot">Documentation completeness — not a prediction of payer approval.</div>
    </div>
  );
}
