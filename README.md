# PSM Tool

Self-service Price Sensitivity Meter toolkit (Van Westendorp + optional Newton-Miller-Smith extension) with Streamlit UI and in-memory report exports.

## Status

This repository is under active build-out across six milestones:

1. Scaffold + privacy baseline
2. Core PSM engine + tests
3. Streamlit upload/results pages
4. PPTX/Excel exports + browser preflight checks
5. SAV loader + NMS extension
6. Docs/CI/deployment polish

## Privacy and Data Hygiene

- Never commit client files.
- Use `data_private/` for local sensitive data only.
- Only synthetic tabular fixtures may be committed in:
  - `src/psm_tool/resources/`
  - `tests/data/`
- Pre-commit blocks `.sav` files and most `.csv`/`.xlsx` paths outside these allowlists.

## Quick Start

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -e .[dev]
pytest -q
streamlit run src/psm_tool/ui/app.py
```

## Chrome/Kaleido Requirement for Static Exports

Plotly static image export uses Kaleido v1 and requires Chrome/Chromium.

- Windows/macOS: install Chrome.
- Linux/VPS/Docker: install Chromium/Chrome.
- Fallback helper:

```bash
python -c "import plotly.io as pio; pio.get_chrome()"
```

If browser discovery fails, set `BROWSER_PATH` (for example `/usr/bin/chromium` in Docker).
