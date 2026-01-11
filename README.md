# Market Workflow App

A personal decision-support dashboard for crypto perpetual futures.  
**"Structure is Authoritative, Price is Ephemeral."**

Converts structural data into actionable trade tickets via a systematic 3-stage filtration workflow.

## Overview

| Stage | Purpose | Description |
|-------|---------|-------------|
| **Stage 1: Trade Ready** | Structural Context | Filters 150+ markets into Trade Ready, Watch, and Ignore bands based on W-1/W-2 structure. |
| **Stage 2: Signal Engine** | Detection | On-demand scanning for Z-Score volume triggers and CVD momentum (11v21) on relevant markets. |
| **Stage 3: Action** | Execution | Exporting formatted tickets for external position management. |

## Feature Set

- **Dynamic Filters**: Filter by Regime (Balanced/Trending), HTF Direction, Price Interaction, and Bias Compatibility.
- **Persistence**: Snapshot-based workflow. Data persists across navigation until manual refresh.
- **CSV Export**: Export the current refined market view with structured timestamps.
- **VPS Native**: Designed for Docker deployment on non-US VPS to bypass Binance geo-restrictions.

## Data Foundations

- **Structural**: BigQuery `core.levels_final` (W-1, W-2, Overlap, Migration metrics).
- **Ephemeral**: Binance Futures API (Live price, 30m Klines, CVD).

## Quick Start (VPS Deployment)

The project includes a `deploy.sh` script for rapid deployment from local to VPS.

```bash
# Locally
./deploy.sh
```

This script:
1. Syncs files via `rsync` (excludes `.git`, `__pycache__`).
2. SSHs into VPS.
3. Rebuilds and restarts the Docker container.

## Configuration

Settings are centralized in `config.py`:
- `TOLERANCE_PCT`: Level test sensitivity (default 0.2%).
- `COMPRESSION_THRESHOLD`: Weekly VA width floor.
- `EXTENDED_THRESHOLD`: Standard deviation for price extension.

## Project Structure

```
market_workflow_app/
├── main.py              # Streamlit entry point & UI
├── config.py            # Global settings & tolerances
├── deploy.sh            # One-click VPS deployment
├── services/
Requested service layers
│   ├── bigquery_service.py
│   └── market_data.py
├── logic/
Core domain logic
│   ├── modules.py       # Context & Primitives
│   ├── relevance.py     # Band Classifier
│   └── signals.py       # Z-Score & CVD Runner
├── Dockerfile
└── docker-compose.yml
```

## License

Personal/Private Use Only.
