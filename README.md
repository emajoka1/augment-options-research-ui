# augment-options-research-ui

Thin Streamlit dashboard for the Options Research Tool.

## What this is

A lightweight local UI that sits on top of the existing research pipeline and Monte Carlo scripts.

Current goals:
- run the existing workflow from a browser
- inspect normalized JSON output
- show key decision/gating data clearly
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
- View summary metrics
- Inspect failures, candidates, provenance, and raw JSON

## Next likely upgrades

- run history viewer
- charts for EV / CVaR / decision changes over time
- artifact browser for `kb/experiments`
- editable risk settings from the UI
- optional FastAPI backend if this grows beyond a local dashboard
