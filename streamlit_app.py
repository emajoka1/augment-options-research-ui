from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Augment Options Research UI", layout="wide")

ROOT = Path(__file__).resolve().parent
DEFAULT_CORE = (ROOT.parent / "augment-options-research-v2" / "project").resolve()
CORE_PATH = Path(os.environ.get("AUGMENT_CORE_PATH", str(DEFAULT_CORE))).expanduser().resolve()
MC_SCRIPT = CORE_PATH / "scripts" / "mc_command.py"
VENV_PY = CORE_PATH / ".venv" / "bin" / "python"
RUN_LOG = CORE_PATH / "snapshots" / "mc_runs.jsonl"
EXPERIMENTS_DIR = CORE_PATH / "kb" / "experiments"
STATE_FILE = CORE_PATH / "snapshots" / "mc_last_state.json"


SAMPLE_PAYLOAD: dict[str, Any] = {
    "timestamp": "2026-03-22T18:21:45.814471+00:00",
    "action_state": "WATCH",
    "final_decision": "PASS",
    "data_status": "OK_FALLBACK",
    "spot": 653.27,
    "regime": "Risk-off",
    "trend": "down_or_flat",
    "data_source": "cboe-delayed-public",
    "symbols_with_data": 0,
    "trade_ready_rule": {
        "pass": False,
        "ev_mean_R": 0.1006,
        "ev_seed_p5_R": 0.0593,
        "ev_stress_mean_R": 0.0901,
        "pl_p5_R": -0.5655,
        "cvar_worst_R": -0.5876,
        "failures": ["pl_p5_not_above_threshold", "structural_quality_below_threshold"],
    },
    "mc_provenance": {
        "model": "jump",
        "n_batches": 10,
        "paths_per_batch": 500,
        "n_total_paths": 5000,
        "source_stale": False,
    },
    "top_candidate": {
        "type": "debit",
        "decision": "PASS",
        "gate_failures": ["NO_CANDIDATES: risk_cap too low for this DTE/structure under current IV/spreads."],
    },
    "raw": {
        "TRADE BRIEF": {
            "NoCandidatesReason": "NO_CANDIDATES: risk_cap too low for this DTE/structure under current IV/spreads.",
            "Candidates": [],
        }
    },
}


def python_bin() -> str:
    if VENV_PY.exists():
        return str(VENV_PY)
    return sys.executable


def core_ready() -> tuple[bool, str]:
    if not CORE_PATH.exists():
        return False, f"Core path not found: {CORE_PATH}"
    if not MC_SCRIPT.exists():
        return False, f"Missing script: {MC_SCRIPT}"
    return True, "OK"


def run_mc_command(
    skip_live: bool,
    max_attempts: int,
    retry_delay_sec: int,
    freshness_sla_seconds: int,
    env_overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str, int]:
    cmd = [
        python_bin(),
        "scripts/mc_command.py",
        "--json",
        "--max-attempts",
        str(max_attempts),
        "--retry-delay-sec",
        str(retry_delay_sec),
        "--freshness-sla-seconds",
        str(freshness_sla_seconds),
    ]
    if skip_live:
        cmd.append("--skip-live")

    env = os.environ.copy()
    for key, value in (env_overrides or {}).items():
        if value is None or value == "":
            continue
        env[str(key)] = str(value)

    proc = subprocess.run(cmd, cwd=CORE_PATH, capture_output=True, text=True, env=env)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    payload = None
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = None

    logs = "\n\n".join(part for part in [stdout, stderr] if part)
    return payload, logs, proc.returncode


def maybe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def load_runs(limit: int = 200) -> list[dict[str, Any]]:
    if not RUN_LOG.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in RUN_LOG.read_text(errors="ignore").splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def load_experiment_artifacts(limit: int = 100) -> list[tuple[Path, dict[str, Any]]]:
    if not EXPERIMENTS_DIR.exists():
        return []
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(EXPERIMENTS_DIR.glob("options-mc-*.json"), reverse=True)[:limit]:
        payload = maybe_load_json(path)
        if payload is not None:
            out.append((path, payload))
    return out


def iso_to_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def metric_value(label: str, value: Any) -> None:
    st.metric(label, "—" if value is None else value)


def status_badge(value: Any) -> str:
    if value is None:
        return "⚪ unknown"
    text = str(value).upper()
    if any(tok in text for tok in ["FAIL", "NO_TRADE", "ERROR"]):
        return f"🔴 {value}"
    if any(tok in text for tok in ["WATCH", "PARTIAL", "STALE"]):
        return f"🟠 {value}"
    if any(tok in text for tok in ["PASS", "OK", "TRADE_READY"]):
        return f"🟢 {value}"
    return f"⚪ {value}"


def summarize_runs(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    data = []
    for row in rows:
        tr = row.get("trade_ready_rule") or {}
        data.append(
            {
                "timestamp": row.get("timestamp"),
                "action_state": row.get("action_state"),
                "final_decision": row.get("final_decision"),
                "data_status": row.get("data_status"),
                "spot": row.get("spot"),
                "ev_mean_R": tr.get("ev_mean_R"),
                "ev_stress_mean_R": tr.get("ev_stress_mean_R"),
                "pl_p5_R": tr.get("pl_p5_R"),
                "cvar_worst_R": tr.get("cvar_worst_R"),
            }
        )
    df = pd.DataFrame(data)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df


def artifacts_dataframe(items: list[tuple[Path, dict[str, Any]]]) -> pd.DataFrame:
    rows = []
    for path, payload in items:
        metrics = payload.get("metrics") or {}
        gates = payload.get("gates") or {}
        rows.append(
            {
                "file": path.name,
                "generated_at": payload.get("generated_at"),
                "status": payload.get("status"),
                "allow_trade": gates.get("allow_trade"),
                "ev": metrics.get("ev"),
                "pop": metrics.get("pop"),
                "cvar95": metrics.get("cvar95"),
                "n_total_paths": payload.get("n_total_paths"),
                "model": (payload.get("assumptions") or {}).get("model"),
                "strategy": (payload.get("assumptions") or {}).get("strategy"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty and "generated_at" in df.columns:
        df["generated_at"] = pd.to_datetime(df["generated_at"], errors="coerce", utc=True)
    return df


def render_payload(payload: dict[str, Any], logs: str, code: int | None) -> None:
    trade_ready = payload.get("trade_ready_rule") or {}
    provenance = payload.get("mc_provenance") or {}
    top_candidate = payload.get("top_candidate") or {}
    raw = payload.get("raw") or {}
    brief = raw.get("TRADE BRIEF") or {}
    failures = trade_ready.get("failures") or []
    candidates = brief.get("Candidates") or []

    st.subheader("Latest workflow result")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_value("Action", status_badge(payload.get("action_state")))
    with c2:
        metric_value("Decision", status_badge(payload.get("final_decision")))
    with c3:
        metric_value("Data status", status_badge(payload.get("data_status")))
    with c4:
        metric_value("Spot", payload.get("spot"))
    with c5:
        metric_value("Exit code", code if code is not None else "—")

    c6, c7, c8, c9 = st.columns(4)
    with c6:
        metric_value("Regime", payload.get("regime"))
    with c7:
        metric_value("Trend", payload.get("trend"))
    with c8:
        metric_value("Data source", payload.get("data_source"))
    with c9:
        metric_value("Symbols with data", payload.get("symbols_with_data"))

    st.subheader("Trade readiness")
    t1, t2, t3, t4, t5 = st.columns(5)
    with t1:
        metric_value("Pass", trade_ready.get("pass"))
    with t2:
        metric_value("EV mean R", trade_ready.get("ev_mean_R"))
    with t3:
        metric_value("EV stress mean R", trade_ready.get("ev_stress_mean_R"))
    with t4:
        metric_value("P/L p5 R", trade_ready.get("pl_p5_R"))
    with t5:
        metric_value("CVaR worst R", trade_ready.get("cvar_worst_R"))

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Why not trade?")
        if failures:
            for failure in failures:
                st.error(failure)
        else:
            st.success("No trade-readiness failures reported.")

        no_cand = brief.get("NoCandidatesReason")
        if no_cand:
            st.warning(no_cand)

        st.subheader("Top candidate")
        st.json(top_candidate)

    with right:
        st.subheader("MC provenance")
        st.json(provenance)

    st.subheader("Candidates")
    if candidates:
        for cand in candidates:
            with st.expander(f"{cand.get('type', 'candidate')} · decision={cand.get('decision')}"):
                st.json(cand)
    else:
        st.info("No candidates returned.")

    tab1, tab2 = st.tabs(["Normalized JSON", "Logs"])
    with tab1:
        st.json(payload)
    with tab2:
        st.text(logs or "No logs captured.")


st.title("Augment Options Research UI")
st.caption("Research dashboard for the existing Monte Carlo, brief, and artifact workflow.")

ready, reason = core_ready()
if not ready:
    st.error(reason)
    st.stop()

if "last_payload" not in st.session_state:
    st.session_state.last_payload = maybe_load_json(STATE_FILE) or SAMPLE_PAYLOAD
if "last_logs" not in st.session_state:
    st.session_state.last_logs = ""
if "last_code" not in st.session_state:
    st.session_state.last_code = None

with st.sidebar:
    st.subheader("Core repo")
    st.code(str(CORE_PATH))
    st.caption(f"Python: {python_bin()}")
    st.divider()

    st.subheader("Run settings")
    skip_live = st.checkbox("Skip live snapshot", value=False)
    max_attempts = st.number_input("Max attempts", min_value=1, max_value=10, value=2, step=1)
    retry_delay_sec = st.number_input("Retry delay (sec)", min_value=0, max_value=3600, value=1, step=1)
    freshness_sla_seconds = st.number_input("Freshness SLA (sec)", min_value=60, max_value=86400, value=7200, step=60)

    st.subheader("Risk / feed overrides")
    max_risk_dollars = st.number_input("SPY_MAX_RISK_DOLLARS", min_value=1.0, max_value=10000.0, value=250.0, step=25.0)
    account_size = st.number_input("SPY_ACCOUNT_SIZE", min_value=100.0, max_value=10000000.0, value=10000.0, step=500.0)
    risk_pct = st.number_input("SPY_RISK_PCT", min_value=0.001, max_value=1.0, value=0.025, step=0.005, format="%.3f")
    min_oi = st.number_input("SPY_MIN_OI", min_value=0, max_value=1000000, value=1000, step=100)
    min_vol = st.number_input("SPY_MIN_VOL", min_value=0, max_value=1000000, value=100, step=50)
    max_spread_pct = st.number_input("SPY_MAX_SPREAD_PCT", min_value=0.0, max_value=1.0, value=0.10, step=0.01, format="%.2f")

    env_overrides = {
        "SPY_MAX_RISK_DOLLARS": max_risk_dollars,
        "SPY_ACCOUNT_SIZE": account_size,
        "SPY_RISK_PCT": risk_pct,
        "SPY_MIN_OI": min_oi,
        "SPY_MIN_VOL": min_vol,
        "SPY_MAX_SPREAD_PCT": max_spread_pct,
    }

    run_now = st.button("Run workflow", type="primary", use_container_width=True)
    load_state = st.button("Load last saved state", use_container_width=True)
    load_sample = st.button("Load sample payload", use_container_width=True)

if load_state:
    st.session_state.last_payload = maybe_load_json(STATE_FILE) or SAMPLE_PAYLOAD
    st.session_state.last_logs = "Loaded from snapshots/mc_last_state.json"
    st.session_state.last_code = 0

if load_sample:
    st.session_state.last_payload = SAMPLE_PAYLOAD
    st.session_state.last_logs = "Loaded sample payload"
    st.session_state.last_code = 0

if run_now:
    with st.spinner("Running mc_command.py …"):
        payload, logs, code = run_mc_command(
            skip_live,
            int(max_attempts),
            int(retry_delay_sec),
            int(freshness_sla_seconds),
            env_overrides=env_overrides,
        )
        if payload is None:
            st.session_state.last_payload = SAMPLE_PAYLOAD
            st.session_state.last_logs = logs
            st.session_state.last_code = code
            st.error("Command did not return parseable JSON. Showing sample payload until the run issue is fixed.")
        else:
            st.session_state.last_payload = payload
            st.session_state.last_logs = logs
            st.session_state.last_code = code

payload = st.session_state.last_payload
logs = st.session_state.last_logs
code = st.session_state.last_code

render_payload(payload, logs, code)

st.subheader("Run history")
runs = load_runs(limit=200)
runs_df = summarize_runs(runs)
if runs_df.empty:
    st.info("No mc_runs.jsonl history found yet.")
else:
    history_cols = st.columns(4)
    with history_cols[0]:
        metric_value("Logged runs", len(runs_df))
    with history_cols[1]:
        metric_value("Latest spot", runs_df.iloc[-1].get("spot"))
    with history_cols[2]:
        metric_value("Latest action", runs_df.iloc[-1].get("action_state"))
    with history_cols[3]:
        metric_value("Latest decision", runs_df.iloc[-1].get("final_decision"))

    chart_df = runs_df.set_index("timestamp").sort_index()
    numeric_cols = [c for c in ["ev_mean_R", "ev_stress_mean_R", "pl_p5_R", "cvar_worst_R", "spot"] if c in chart_df.columns]
    if numeric_cols:
        st.line_chart(chart_df[numeric_cols], height=260)

    st.dataframe(runs_df.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)

st.subheader("Options MC artifacts")
artifacts = load_experiment_artifacts(limit=100)
artifacts_df = artifacts_dataframe(artifacts)
if artifacts_df.empty:
    st.info("No options-mc artifacts found yet.")
else:
    a1, a2, a3 = st.columns(3)
    with a1:
        metric_value("Artifacts", len(artifacts_df))
    with a2:
        metric_value("Latest model", artifacts_df.iloc[0].get("model"))
    with a3:
        metric_value("Latest strategy", artifacts_df.iloc[0].get("strategy"))

    chart_cols = [c for c in ["ev", "pop", "cvar95"] if c in artifacts_df.columns]
    if chart_cols:
        plot_df = artifacts_df.sort_values("generated_at").set_index("generated_at")
        st.line_chart(plot_df[chart_cols], height=240)

    selected_name = st.selectbox("Inspect artifact", options=artifacts_df["file"].tolist())
    selected_payload = next((payload for path, payload in artifacts if path.name == selected_name), None)

    st.dataframe(artifacts_df, use_container_width=True, hide_index=True)
    if selected_payload is not None:
        st.json(selected_payload)
