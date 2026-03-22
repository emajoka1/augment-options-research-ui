'use client';

import { ChangeEvent, useMemo, useState } from 'react';

type AnyRecord = Record<string, any>;

const starter = `{
  "action_state": "WATCH",
  "final_decision": "PASS",
  "data_status": "OK_FALLBACK",
  "spot": 653.27,
  "regime": "Risk-off",
  "trend": "down_or_flat",
  "data_source": "cboe-delayed-public",
  "symbols_with_data": 0,
  "trade_ready_rule": {
    "pass": false,
    "ev_mean_R": 0.1006,
    "ev_stress_mean_R": 0.0901,
    "pl_p5_R": -0.5655,
    "cvar_worst_R": -0.5876,
    "failures": ["pl_p5_not_above_threshold", "structural_quality_below_threshold"]
  },
  "mc_provenance": {
    "model": "jump",
    "n_batches": 10,
    "paths_per_batch": 500,
    "n_total_paths": 5000,
    "source_stale": false
  },
  "top_candidate": {
    "type": "debit",
    "gate_failures": ["NO_CANDIDATES: risk_cap too low for this DTE/structure under current IV/spreads."]
  },
  "raw": {
    "TRADE BRIEF": {
      "NoCandidatesReason": "NO_CANDIDATES: risk_cap too low for this DTE/structure under current IV/spreads.",
      "Candidates": []
    }
  }
}`;

function fmt(value: any) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

function statusClass(value: string | undefined) {
  const v = (value || '').toUpperCase();
  if (v.includes('PASS') || v.includes('OK')) return 'status-pass';
  if (v.includes('WATCH')) return 'status-watch';
  if (v.includes('FAIL') || v.includes('NO')) return 'status-fail';
  return '';
}

function Metric({ label, value }: { label: string; value: any }) {
  return (
    <div className="metric">
      <label>{label}</label>
      <strong>{fmt(value)}</strong>
    </div>
  );
}

export default function DashboardClient() {
  const [text, setText] = useState(starter);
  const [error, setError] = useState('');

  const payload = useMemo<AnyRecord | null>(() => {
    try {
      setError('');
      return JSON.parse(text);
    } catch (err: any) {
      setError(err?.message || 'Invalid JSON');
      return null;
    }
  }, [text]);

  const trade = payload?.trade_ready_rule || {};
  const provenance = payload?.mc_provenance || {};
  const topCandidate = payload?.top_candidate || {};
  const brief = payload?.raw?.['TRADE BRIEF'] || {};
  const failures = Array.isArray(trade.failures) ? trade.failures : [];
  const candidates = Array.isArray(brief.Candidates) ? brief.Candidates : [];

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    file.text().then(setText).catch(() => setError('Could not read file'));
  }

  return (
    <main className="page">
      <section className="hero">
        <h1>Augment Options Research UI</h1>
        <p>
          Vercel-compatible dashboard for viewing normalized payloads from the options research pipeline. Paste JSON,
          upload an artifact, and inspect decisions, failures, and provenance in the browser.
        </p>
      </section>

      <section className="panel">
        <h2>Input</h2>
        <p className="help">
          This Vercel version is browser-first: it does not shell into a local Python repo. Feed it the JSON output from
          <code> mc_command.py --json</code> or one of your stored artifacts.
        </p>
        <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
          <input type="file" accept="application/json,.json" onChange={onFile} />
          <button className="secondary" onClick={() => setText(starter)}>Load sample</button>
        </div>
        <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} />
        {error && <p className="status-fail">JSON error: {error}</p>}
      </section>

      {payload && (
        <>
          <section className="panel">
            <h2>Summary</h2>
            <div className="grid">
              <Metric label="Action" value={payload.action_state} />
              <Metric label="Decision" value={payload.final_decision} />
              <Metric label="Data status" value={payload.data_status} />
              <Metric label="Spot" value={payload.spot} />
              <Metric label="Regime" value={payload.regime} />
              <Metric label="Trend" value={payload.trend} />
              <Metric label="Data source" value={payload.data_source} />
              <Metric label="Symbols with data" value={payload.symbols_with_data} />
            </div>
          </section>

          <section className="panel">
            <h2>Trade readiness</h2>
            <div className="grid">
              <Metric label="Pass" value={trade.pass} />
              <Metric label="EV mean R" value={trade.ev_mean_R} />
              <Metric label="EV stress mean R" value={trade.ev_stress_mean_R} />
              <Metric label="P/L p5 R" value={trade.pl_p5_R} />
              <Metric label="CVaR worst R" value={trade.cvar_worst_R} />
            </div>
          </section>

          <section className="row">
            <div className="panel">
              <h2>Failures</h2>
              {failures.length ? (
                <ul className="list">
                  {failures.map((failure: string) => (
                    <li key={failure} className="status-fail">{failure}</li>
                  ))}
                </ul>
              ) : (
                <p className="status-pass">No trade-readiness failures reported.</p>
              )}

              <h3>Top candidate</h3>
              <div className="code">{JSON.stringify(topCandidate, null, 2)}</div>
            </div>

            <div className="panel">
              <h2>MC provenance</h2>
              <div className="grid">
                <Metric label="Model" value={provenance.model} />
                <Metric label="Batches" value={provenance.n_batches} />
                <Metric label="Paths / batch" value={provenance.paths_per_batch} />
                <Metric label="Total paths" value={provenance.n_total_paths} />
                <Metric label="Source stale" value={provenance.source_stale} />
              </div>
              <div className="code" style={{ marginTop: 12 }}>{JSON.stringify(provenance, null, 2)}</div>
            </div>
          </section>

          <section className="panel">
            <h2>Candidates</h2>
            {candidates.length ? candidates.map((candidate: AnyRecord, idx: number) => (
              <div className="card" key={`${candidate.type || 'candidate'}-${idx}`}>
                <strong className={statusClass(candidate.decision)}>{candidate.type || 'candidate'} · {fmt(candidate.decision)}</strong>
                <div className="code" style={{ marginTop: 10 }}>{JSON.stringify(candidate, null, 2)}</div>
              </div>
            )) : (
              <p>{brief.NoCandidatesReason || 'No candidates returned.'}</p>
            )}
          </section>

          <section className="panel">
            <h2>Raw payload</h2>
            <div className="code">{JSON.stringify(payload, null, 2)}</div>
          </section>
        </>
      )}
    </main>
  );
}
