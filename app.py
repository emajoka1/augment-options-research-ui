from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st

st.set_page_config(page_title="Augment Options Research UI", layout="wide")

DEFAULT_CORE = (Path(__file__).resolve().parent.parent / "augment-options-research-v2" / "project").resolve()
CORE_PATH = Path(os.environ.get("AUGMENT_CORE_PATH", str(DEFAULT_CORE))).expanduser().resolve()
MC_SCRIPT = CORE_PATH / "scripts" / "mc_command.py"
VENV_PY = CORE_PATH / ".venv" / "bin" / "python"


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


def run_mc_command(skip_live: bool, max_attempts: int, retry_delay_sec: int, freshness_sla_seconds: int) -> tuple[dict[str, Any] | None, str, int]:
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

    proc = subprocess.run(cmd, cwd=CORE_PATH, capture_output=True, text=True)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    payload = None
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            pass

    logs = "\n\n".join(part for part in [stdout, stderr] if part)
    return payload, logs, proc.returncode


def pill(label: str, value: Any) -> None:
    st.metric(label, value if value is not None else "—")


st.title("Augment Options Research UI")
st.caption("Thin local dashboard over the existing Monte Carlo and brief pipeline.")

ready, reason = core_ready()
if not ready:
    st.error(reason)
    st.stop()

with st.sidebar:
    st.subheader("Run settings")
    st.code(str(CORE_PATH))
    skip_live = st.checkbox("Skip live snapshot", value=False)
    max_attempts = st.number_input("Max attempts", min_value=1, max_value=10, value=2, step=1)
    retry_delay_sec = st.number_input("Retry delay (sec)", min_value=0, max_value=3600, value=1, step=1)
    freshness_sla_seconds = st.number_input("Freshness SLA (sec)", min_value=60, max_value=86400, value=7200, step=60)
    run_now = st.button("Run workflow", type="primary")

if "last_payload" not in st.session_state:
    st.session_state.last_payload = None
if "last_logs" not in st.session_state:
    st.session_state.last_logs = ""
if "last_code" not in st.session_state:
    st.session_state.last_code = None

if run_now:
    with st.spinner("Running mc_command.py …"):
        payload, logs, code = run_mc_command(skip_live, int(max_attempts), int(retry_delay_sec), int(freshness_sla_seconds))
        st.session_state.last_payload = payload
        st.session_state.last_logs = logs
        st.session_state.last_code = code

payload = st.session_state.last_payload
logs = st.session_state.last_logs
code = st.session_state.last_code

if payload is None:
    st.info("Press **Run workflow** to execute the existing pipeline and inspect the result.")
    if logs:
        with st.expander("Last logs"):
            st.text(logs)
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    pill("Action", payload.get("action_state"))
with col2:
    pill("Decision", payload.get("final_decision"))
with col3:
    pill("Data status", payload.get("data_status"))
with col4:
    pill("Spot", payload.get("spot"))
with col5:
    pill("Exit code", code)

col6, col7, col8, col9 = st.columns(4)
with col6:
    pill("Regime", payload.get("regime"))
with col7:
    pill("Trend", payload.get("trend"))
with col8:
    pill("Data source", payload.get("data_source"))
with col9:
    pill("Symbols with data", payload.get("symbols_with_data"))

trade_ready = payload.get("trade_ready_rule") or {}
provenance = payload.get("mc_provenance") or {}
top_candidate = payload.get("top_candidate") or {}
raw = payload.get("raw") or {}
brief = raw.get("TRADE BRIEF") or {}

st.subheader("Trade readiness")
tr1, tr2, tr3, tr4, tr5 = st.columns(5)
with tr1:
    pill("Pass", trade_ready.get("pass"))
with tr2:
    pill("EV mean R", trade_ready.get("ev_mean_R"))
with tr3:
    pill("EV stress mean R", trade_ready.get("ev_stress_mean_R"))
with tr4:
    pill("P/L p5 R", trade_ready.get("pl_p5_R"))
with tr5:
    pill("CVaR worst R", trade_ready.get("cvar_worst_R"))

left, right = st.columns([1, 1])
with left:
    st.subheader("Failures")
    failures = trade_ready.get("failures") or []
    if failures:
        for failure in failures:
            st.error(failure)
    else:
        st.success("No trade-readiness failures reported.")

    st.subheader("Top candidate")
    st.json(top_candidate)

with right:
    st.subheader("MC provenance")
    st.json(provenance)

st.subheader("Candidates")
candidates = brief.get("Candidates") or []
if candidates:
    for cand in candidates:
        with st.expander(f"{cand.get('type', 'candidate')} · decision={cand.get('decision')}"):
            st.json(cand)
else:
    st.info("No candidates returned.")

st.subheader("Raw payload")
tab1, tab2 = st.tabs(["Normalized JSON", "Logs"])
with tab1:
    st.json(payload)
with tab2:
    st.text(logs or "No logs captured.")
