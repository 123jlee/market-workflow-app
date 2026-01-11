# Market Workflow App

A personal decision-support dashboard for crypto perpetual futures.  
Converts **structure → events → commitment** and surfaces ideas worth acting on.

## Overview

| Stage | Purpose |
|-------|---------|
| **Stage 1: Trade Readiness** | Filter markets by structural relevance |
| **Stage 2: Signal Engine** | Detect actionable triggers (Z-Score, CVD) |
| **Stage 3: Export** | Copy tickets to external tools |

## Data Sources

| Layer | Source | Role |
|-------|--------|------|
| **Structural** | BigQuery `core.levels_final` | Authoritative (D-1, W-1 levels) |
| **Ephemeral** | Binance Futures API | Live prices, klines, CVD |

## Quick Start

### Local Development (Mock Data)
```bash
pip install -r requirements.txt
streamlit run main.py
```

### Production (Docker on VPS)
```bash
scp -r . user@your-vps:/path/to/app
ssh user@your-vps
cd /path/to/app
docker compose up --build -d
```

## Configuration

Edit `config.py`:
- `USE_MOCK_DATA`: `True` for local dev, `False` for live.
- `BINANCE_PROXY_URL`: Optional proxy for US geo-restrictions.

## Project Structure
```
market_workflow_app/
├── main.py              # Streamlit entry point
├── config.py            # Settings
├── services/
│   ├── bigquery_service.py
│   └── market_data.py
├── logic/
│   ├── modules.py       # Context primitives
│   └── relevance.py     # Band classifier
├── Dockerfile
└── docker-compose.yml
```

## License
Private / Personal Use
