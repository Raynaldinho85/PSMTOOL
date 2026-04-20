# Release Candidate Handover Checklist

Date: 2026-04-20

## 1. Current Release Candidate Status

- Target status: **Yellow -> customer-near demo release**
- Latest audit: see [final_release_audit.md](./final_release_audit.md)
- Current code quality gates:
  - `ruff check .` -> pass
  - `ruff format --check .` -> pass
  - `pytest -q -rs` -> pass with environment-dependent export skips

## 2. Intended Release Scope (Current Working Tree)

The current release candidate scope is broader than a single bugfix. It includes:

### Core product behavior
- PSM / NMS / Turnover / Profit logic updates
- Quality-control and validation behavior
- Tested Price / marker-label placement behavior
- export payload propagation

### UI / customer-facing app
- app shell
- upload
- results
- export
- knowledge / methodology
- navigation / language switch
- runtime i18n support

### Export surfaces
- static PNG rendering path
- KPI summary image
- PPTX generation
- export wording / summary logic

### Tests
- read/validate
- chart placement and layout
- export coverage
- i18n coverage
- results helpers / payload builder

## 3. Final Pre-Handover Manual Checks

These are the last recommended human checks before handing the tool to a customer:

### A. Startup / access
- [ ] fresh venv starts successfully with README commands
- [ ] app opens on `streamlit run src/psm_tool/ui/app.py`
- [ ] optional password gate works if `APP_PASSWORD` is set

### B. Upload flow
- [ ] CSV upload works
- [ ] XLSX upload works
- [ ] SAV is **not** offered in the public upload flow
- [ ] upload privacy copy matches actual behavior
- [ ] validation messages are understandable in EN and DE

### C. Results / charts
- [ ] product + segment selection works
- [ ] tested price toggle/input works
- [ ] marker override controls work
- [ ] charts render without obvious mixed-language artifacts
- [ ] KPI cards do not clip important German labels

### D. Export
- [ ] PNG export works on the target runtime with Chrome/Chromium available
- [ ] PPTX export works on the target runtime with Chrome/Chromium available
- [ ] PPTX titles and summary text fit on slides
- [ ] marker overrides from Results match PPTX output
- [ ] KPI summary is consistent between Results and export

### E. Language / copy
- [ ] EN/DE switch works on all main pages
- [ ] sidebar navigation labels are consistent
- [ ] Knowledge & Methodology / Methodik labels are consistent
- [ ] no obvious leftover English strings in the DE flow

## 4. Customer-Facing Known Constraints

These should be communicated clearly if relevant:

- SAV uploads are intentionally disabled in the public app flow so uploaded data remains fully in-memory.
- Static PNG/PPTX export requires Chrome/Chromium for Kaleido.
- The tool is a public demo-style pricing analytics workflow, not a multi-user persistent data system.
- Uploaded files are intended to remain session-based and not persist by default.

## 5. Deployment Notes

### Best current deployment path
- Docker / own server / VPS

### Also realistic
- local managed Windows setup via `.venv` + `start_server.bat`

### Still requires environment validation
- export runtime with Chrome/Chromium present

## 6. Recommended Release Packaging

For a clean handover, package or freeze:

- source tree at a clean commit/tag
- `README.md`
- `.streamlit/config.toml`
- `Dockerfile`
- `docker-compose.yml`
- `start_server.bat`
- `docs/final_release_audit.md`
- `docs/i18n_translation_inventory_de_review.csv`

## 7. What Still Needs Cleanup Before a Formal Release Tag

- convert the current dirty working tree into a clean committed release snapshot
- decide whether all current modified/untracked files are intended for the release tag
- run one final export smoke test on the actual target deployment environment

## 8. Suggested Release Decision

If the target environment has working Chrome/Chromium for Kaleido and the manual checks above pass:

- **OK for first customer-near demo release**

If export cannot be validated on the target runtime yet:

- **Hold release until one real export smoke test is completed**
