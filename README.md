# PSM Tool

Public demo repository for a self-service pricing analytics workflow:

- Van Westendorp Price Sensitivity Meter (PSM)
- Optional NMS Trial/Revenue extension
- Streamlit UI for upload, analysis, and export
- PPTX and Excel exports generated fully in-memory

No AI or external API is required at runtime.

## Privacy and Data Hygiene

Never commit client data.

- Local sensitive files: `data_private/` only
- Synthetic/demo fixtures only:
  - `src/psm_tool/resources/`
  - `tests/data/`
- Pre-commit blocks:
  - anything under `data_private/`
  - all `*.sav`
  - `*.csv` and `*.xlsx` outside allowlisted folders
  - files larger than 5 MB

## Input Template (MVP)

One row per respondent per product.

Required columns:

- `respondent_id`
- `segment`
- `currency`
- `too_cheap`
- `bargain`
- `expensive_acceptable`
- `too_expensive`

Recommended:

- `product_id`

Optional:

- `weight`
- `puki` (1..5)
- `pi_bargain_pct` (percent 0..100, fraction 0..1, or coded 1..11)
- `pi_expensive_pct` (percent 0..100, fraction 0..1, or coded 1..11)

Supported uploads:

- `.csv`
- `.xlsx`

## Quality Checks

PSM validity rule per respondent:

- `too_cheap < bargain < expensive_acceptable < too_expensive`

Behavior:

- PSM curves/KPIs are computed on valid respondents only
- Inconsistent and missing cases stay visible in QC reporting
- Missing values are excluded metric-wise during curve computation
- Negative price values are treated as missing (not clamped), then excluded identically
  to other missing values across PSM/NMS/Turnover/Revenue calculations

## PSM Computation

Curves over price grid:

- Too Cheap: `% (too_cheap >= p)`
- Bargain: `% (bargain >= p)`
- Expensive: `% (expensive_acceptable <= p)`
- Too Expensive: `% (too_expensive <= p)`
- Derived:
  - Not Bargain = `100 - Bargain`
  - Not Expensive = `100 - Expensive`

KPI intersections (linear interpolation):

- OPP: Too Cheap vs Too Expensive
- IDP: Bargain vs Expensive
- PMI: Too Cheap vs Not Bargain
- PME: Too Expensive vs Not Expensive
- Accepted range: `[PMI, PME]`
- Price stress: `OPP - IDP`

No clean crossing cases are handled via closest approach or overlap interval status.

## Grid Defaults (locked)

- Mode: `auto`
- Snap: `on` by default
- Currency increments:
  - `EUR: 5`
  - `SEK: 20`
  - `CHF: 5`
- Unknown currency: snap increment not applied

When increment is available:

- `min_price = floor(raw_min / inc) * inc`
- `max_price = ceil(raw_max / inc) * inc`
- `step >= inc` and rounded up to increment multiple
- Grid is unique, sorted, and includes `max_price`

UI exposes:

- auto/manual grid mode
- snap on/off toggle
- increment used and final min/max/step

## NMS Extension

Respondent-level piecewise curve:

- `(too_cheap, 0)`
- `(bargain, pi_bargain_pct)`
- `(expensive_acceptable, pi_expensive_pct)`
- `(too_expensive, 0)`

PI values are clamped to `[0, 100]`. No monotonic forcing is applied.

PI preprocessing guardrails:

- If both PI columns are detected as coded scale `1..11`, they are mapped to percent via
  `pct = 10 + (code - 1) * 9`.
- If both PI columns are detected as fractions `0..1`, they are normalized to percent
  with conservative safeguards.

Population default:

- PSM-valid respondents
- If `puki` exists: include `puki <= 2` by default
- Optional UI toggle includes neutral: `puki <= 3`
- If `puki` missing: include all and report filter not applied

NMS outputs:

- Trial %
- Revenue per 100
- Turnover index
- MaxTrial price
- MaxRevenue price

## Packaged Demo Resources

- `src/psm_tool/resources/sample_psm.csv` is shipped in distributions
- Dataset contains multiple segments/currencies (`DE/EUR`, `SE/SEK`) and PI columns
- Upload page provides:
  - in-memory CSV template download
  - in-memory XLSX template download
  - load packaged synthetic example via `importlib.resources`

SAV uploads are intentionally disabled in the public app flow because uploaded files must
remain fully in-memory. If SAV input is needed later, it should only be reintroduced with a
compliant in-memory parsing path.

## Install and Run

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -e .[dev]
pytest -q
streamlit run src/psm_tool/ui/app.py
```

Optional developer-only SAV path tests:

```bash
pip install -e .[sav]
```

## Offline Install (Wheelhouse)

Build wheelhouse on an online machine:

```bash
pip download -d wheelhouse -e .[dev]
```

Install on an offline machine:

```bash
pip install --no-index --find-links=wheelhouse -e .[dev]
```

## Chrome/Kaleido Static Export Requirements

Static image export uses:

- `plotly>=6.1.1`
- `kaleido>=1.0.0`

Kaleido v1 needs Chrome/Chromium.

### Windows/macOS

- Install Chrome normally.

### Linux/VPS

- Install Chromium/Chrome via system package manager.

### Fallback helper

```bash
python -c "import plotly.io as pio; pio.get_chrome()"
```

If browser discovery fails, set `BROWSER_PATH`.

Docker image sets:

- `BROWSER_PATH=/usr/bin/chromium`

## Deployment

### Docker

```bash
docker compose up --build
```

Container characteristics:

- Debian slim base
- Installs Chromium via `apt`
- Runs Streamlit on port `8501`

### Linux VPS + reverse proxy (nginx)

Run Streamlit as a service:

```bash
streamlit run src/psm_tool/ui/app.py --server.address 127.0.0.1 --server.port 8501
```

Proxy `/` to `http://127.0.0.1:8501` via nginx.

### Streamlit Community Cloud (demo)

For the quickest free demo deploy, use Streamlit Community Cloud with:

- main file: `src/psm_tool/ui/app.py`
- Python version: `3.11`
- root `requirements.txt`
- root `packages.txt`
- secrets for `DEMO_MODE` and `APP_PASSWORD`

See `docs/streamlit_community_cloud_demo.md` for the exact setup and smoke-test checklist.

## Environment Variables

- `DEMO_MODE=true|false`
  - enables strict upload limit behavior and reduced raw-data visibility
- `APP_PASSWORD=<value>`
  - optional simple access gate; empty means public
- `MAX_UPLOAD_MB` (default `25`)
- `MAX_ROWS_DEMO` (default `5000`)

## CI

`/.github/workflows/ci.yml` contains:

- default matrix: Python `3.11`, `3.12`, `3.13`
  - installs `.[dev]`
  - runs `python -c "import plotly.io as pio; pio.get_chrome()"`
  - runs ruff + pytest (`-m "not sav"`)
- SAV job: Python `3.11`
  - installs `.[dev,sav]`
  - runs SAV-marked tests (`-m "sav"`)
  - SAV tests only verify local path-based parsing; upload-bytes SAV is intentionally blocked

## Test Suite Highlights

- Unit tests for validation, grid, curves, intersections, metrics, QC, NMS
- Golden master regression test with fixed synthetic expected KPIs
- Export integration tests:
  - Plotly PNG rendering path
  - PPTX end-to-end generation
