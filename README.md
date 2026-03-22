# augment-options-research-ui

Thin Streamlit dashboard for the Options Research Tool.

## What this is

A lightweight local UI that sits on top of the existing research pipeline and Monte Carlo scripts.

Current goals:
- run the existing workflow from a browser
- inspect normalized JSON output
- show key decision/gating data clearly
- browse recent run history and artifacts
- avoid rewriting the core engine

## Expected local setup

This UI expects the original project checkout to exist locally at one of these paths:
- `../augment-options-research-v2/project` (default)
- or a custom path via `AUGMENT_CORE_PATH`

## Run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Compatibility alias:

```bash
streamlit run app.py
```

## Optional env vars

```bash
export AUGMENT_CORE_PATH=/absolute/path/to/augment-options-research-v2/project
```

## Current features

- Run `scripts/mc_command.py --json`
- Toggle `--skip-live`
- Adjust attempts / retry delay / freshness SLA
- Override key risk/feed env settings from the sidebar
  - `SPY_MAX_RISK_DOLLARS`
  - `SPY_ACCOUNT_SIZE`
  - `SPY_RISK_PCT`
  - `SPY_MIN_OI`
  - `SPY_MIN_VOL`
  - `SPY_MAX_SPREAD_PCT`
- Load the latest saved state or a sample payload
- View summary metrics and trade-readiness gates
- Inspect failures, candidates, provenance, and raw JSON
- Browse `snapshots/mc_runs.jsonl` history
- Chart recent EV / CVaR / spot metrics
- Browse `kb/experiments/options-mc-*.json` artifacts

## App entrypoints

- `streamlit_app.py` — main Streamlit app with all relevant code
- `app.py` — compatibility shim that imports `streamlit_app.py`

## Next likely upgrades

- editable risk settings from the UI
- compare two artifacts side-by-side
- surface more of the gate logic in human language
- export a lightweight HTML/PDF report
- optional FastAPI backend if this grows beyond a local dashboard
