# augment-options-research-ui

Self-contained Streamlit dashboard for the Options Research Tool.

## What changed

The relevant workflow engine code is now bundled directly into this repo under `vendor_core/`.

That means:
- no sibling repo dependency
- no `AUGMENT_CORE_PATH` setup
- one repo to clone
- one app to run

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

## App entrypoints

- `streamlit_app.py` — main Streamlit app with all relevant code
- `app.py` — compatibility shim that imports `streamlit_app.py`

## Repo layout

- `streamlit_app.py` — Streamlit UI
- `vendor_core/src/` — bundled Python core package code
- `vendor_core/scripts/` — bundled workflow scripts
- `vendor_core/snapshots/` — generated runtime state/history (created as you run)
- `vendor_core/kb/experiments/` — generated MC artifacts (created as you run)

## Current features

- Run bundled `mc_command.py --json`
- Run a one-click smoke test from the UI
- View a self-check table for required bundled files
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
- Show a friendlier workflow diagnostic when a run fails
- Browse `vendor_core/snapshots/mc_runs.jsonl` history
- Chart recent EV / CVaR / spot metrics
- Browse `vendor_core/kb/experiments/options-mc-*.json` artifacts

## Notes

- This is now much more reliable for local use because the engine ships with the UI.
- Some live-data functionality still depends on external connectivity and whatever market data sources the scripts call.
- Generated artifacts are intentionally not vendored from the old repo; they are recreated in this repo as you use the app.
