# augment-options-research-ui

Vercel-compatible UI for the Options Research Tool.

## What changed

The first version was a local Streamlit shell that called a sibling Python repo. That does **not** fit Vercel well.

This version is rebuilt as a **Next.js app** so it can deploy cleanly on Vercel.

## Current model

This UI is now **browser-first**:
- paste normalized JSON from `scripts/mc_command.py --json`
- or upload a `.json` artifact from your pipeline
- inspect decision state, failures, candidates, and MC provenance

That makes it deployable on Vercel without depending on:
- local shell access
- a sibling checkout
- Python processes on the host machine

## Local development

```bash
npm install
npm run dev
```

Then open:

```bash
http://localhost:3000
```

## Deploy on Vercel

The repo is now a standard Next.js app, so Vercel should detect it automatically.

Typical flow:
1. Import the GitHub repo into Vercel
2. Framework preset: **Next.js**
3. Build command: `next build` (default)
4. Output: automatic

## What the UI currently shows

- action / decision / data status
- regime / trend / spot / source
- trade readiness metrics
- failure reasons
- top candidate
- MC provenance
- candidates block
- raw JSON payload viewer

## Good next upgrades

- add a JSON artifact history browser
- add charts for EV / CVaR / decision changes
- support fetching payloads from a backend API
- add authentication if you want private hosted access
- add a real API layer for running the engine remotely

## Important limitation

This repo is now **Vercel-compatible**, but it does **not** run the core Python/MC engine on Vercel by itself.

If you want remote execution too, the next step is to build either:
- a small backend service that runs the engine and returns JSON, or
- an API ingestion flow where your core pipeline uploads fresh artifacts for the UI to read
