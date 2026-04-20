# Final Release Audit - PSMTOOL

Audit date: 2026-04-20  
Audited working tree: local current working tree (dirty / not a clean commit)  
Scope: repository audit only; no source-code fixes applied

## A) Executive Summary

**Release status: Yellow**

**Why**

The repository is close to a customer-facing demo state and is now **releaseable with a few known residual risks**, not a hard blocker state.

Primary concerns that remain:

- the audited state is a **dirty local worktree**, so there is no clean audited release snapshot yet
- local export tests that require Chrome/Chromium were skipped in this environment, so export quality is only partially verified locally
- one repo-hygiene item remains (`PSMTOOL.code-workspace` should stay ignored / untracked)

## B) Blockers

No current code-level blockers remain after the SAV upload guardrail fix.

## C) High Priority Issues

1. **No clean audited release snapshot exists yet**  
   - **Evidence:** `git status --short` shows many modified and untracked files across `src/`, `tests/`, `docs/`, and repo-root artifacts such as `PSMTOOL.code-workspace`.  
   - **Impact:** The audited state is reproducible only as a local working tree, not as a clean tagged revision. This increases release risk and makes rollback/support harder.

2. **Local export audit is incomplete without Chrome/Chromium**  
   - **Evidence:** 5 export-related tests in `tests/test_report_exports.py` were skipped locally because Kaleido could not find a browser runtime.  
   - **Impact:** PNG/PPTX export logic is covered by tests and CI design, but this local audit could not fully verify the export path end-to-end on this machine.

## D) Medium / Low Priority Issues

1. **Repo hygiene: local workspace file not ignored**  
   - `PSMTOOL.code-workspace` is untracked and appears user/machine-specific.  
   - `.gitignore` is otherwise solid, but adding a `*.code-workspace` ignore rule would reduce accidental commits.

2. **Repo hygiene: generated/reference artifacts may deserve curation**  
   - `Theory/._extracted_text/*.txt` is tracked. These look like generated reference text artifacts rather than runtime essentials.  
   - Not a blocker, but worth deciding explicitly whether they belong in the product repo.

3. **Partial local-only i18n surface**  
   - The current working tree includes untracked i18n assets/tests (`src/psm_tool/i18n/`, `tests/test_i18n.py`).  
   - Audit result therefore applies to the **current working tree**, not to a known committed baseline.

4. **Windows-first convenience path is stronger than Linux portable guidance**  
   - `start_server.bat` makes Windows local startup easy.
   - Linux/VPS and Docker are documented, but there is no equivalent lightweight Linux helper script.

## E) Test-Ergebnisse

### Commands executed

1. `.\.venv\Scripts\python.exe -m ruff check .`  
   - **Result:** passed

2. `.\.venv\Scripts\python.exe -m ruff format --check .`  
   - **Result:** passed

3. `.\.venv\Scripts\python.exe -m pytest -q`  
   - **Result:** passed with skips

4. `.\.venv\Scripts\python.exe -m pytest -q -rs`  
   - **Result:** passed with skip reasons printed

### Relevant skips

- `tests/test_read_any.py:46`  
  `pyreadstat is installed; missing-dependency scenario not applicable.`

- `tests/test_report_exports.py:93`
- `tests/test_report_exports.py:156`
- `tests/test_report_exports.py:279`
- `tests/test_report_exports.py:303`
- `tests/test_report_exports.py:319`  
  All skipped because Chrome/Chromium was unavailable for Kaleido in the local audit environment.

### Coverage observations by area

| Area | Evidence |
|---|---|
| PSM core | `tests/test_metrics.py`, `tests/test_curves.py`, `tests/test_intersections.py`, `tests/test_golden_master.py` |
| NMS / PI / Turnover | `tests/test_nms.py`, `tests/test_turnover_index.py`, `tests/test_secondary_plot_layouts.py` |
| Tested Price / marker placement | `tests/test_psm_plot.py`, `tests/test_secondary_plot_layouts.py`, `tests/test_results_helpers.py`, `tests/test_benchmarks.py` (local working tree) |
| KPI Summary / PPTX / PNG export | `tests/test_report_exports.py`, `tests/test_kpi_summary_png.py` (local working tree) |
| i18n / Knowledge | `tests/test_knowledge_page.py`, `tests/test_i18n.py` (local working tree) |
| Upload / validation | `tests/test_validate.py`, `tests/test_read_any.py`, `tests/test_upload_state.py` |

## F) Funktionscheck

| Feature | Status | Risiko | Kommentar |
|---|---|---:|---|
| Upload CSV/XLSX | OK | Low | Reader path uses `BytesIO` for upload bytes. |
| Upload SAV | OK with explicit limitation | Medium | App upload flow blocks SAV bytes to preserve in-memory-only handling; local path-based helper support remains for developer/test use. |
| Template validation | OK | Low | Good direct test coverage in `tests/test_validate.py`. |
| PSM computation | OK | Low | Solid unit/regression coverage. |
| NMS / PI / Turnover | OK | Low-Med | Covered by unit tests; behavior appears consistent. |
| PUKI filter | OK | Low | Tested and integrated in payload/results flow. |
| Tested Price | OK | Low | Covered in plot/result helper tests. |
| Marker label placement + manual overrides | OK | Low-Med | Good focused tests; visual behavior not browser-smoke-tested in this audit. |
| KPI Summary | OK | Medium | Tests exist; local export/browser-dependent rendering not fully exercised. |
| PNG export | Partially verified | Medium | Codepath and tests present, but local browser-dependent checks skipped. |
| PPTX export | Partially verified | Medium | Same as PNG export. |
| DE/EN switch | OK | Medium | Functional in current working tree; some nav label behavior relies on UI-layer customization. |
| Knowledge & Methodology | OK | Low | Content and import path tested. |
| No persistent data storage | OK | Low-Med | Session-state usage is appropriate; public upload flow now avoids disk-backed SAV parsing. |

## G) Export-Check

| Export area | Status | Basis | Notes |
|---|---|---|---|
| PNG background white | Likely OK | code + tests | `prepare_figure_for_static_export(...)` applies white theme; local end-to-end render not fully exercised due missing browser. |
| Charts not distorted | Likely OK | code + tests | PPTX builder uses contained-fit image placement helpers. |
| PPTX charts not distorted | Likely OK | code + tests | `_contained_rect(...)` and `_add_picture_contained(...)` are covered in tests. |
| PPTX titles within slide | Likely OK | tests | `tests/test_report_exports.py` checks shape bounds and title fitting helpers. |
| PPTX summaries within slide | Likely OK | tests | Shape-bound checks present; full visual review on target viewer still recommended. |
| Marker overrides preserved into PPTX | OK | tests + code | `payload_builder.py` and `pptx_builder.py` pass override maps through; direct tests exist. |
| KPI Summary consistency | Likely OK | tests + code | Shared export path exists; browser-dependent rendering not fully exercised locally. |
| File naming clarity | OK | code review | Names like `psm_report_{product}_{segment}.pptx` and `kpi_summary_{product}_{segment}.png` are understandable. |

**Export audit conclusion:** structurally strong, but still benefits from one real smoke pass in the target deployment environment because local browser-backed export tests were skipped.

## H) i18n-Check

- **Language setting:** present in current working tree and session-based (`app_language`)
- **Knowledge & Methodology:** covered by dedicated content tests
- **Navigation:** present, but current working tree includes untracked i18n/nav test assets
- **Known migration status:** the repo now contains both runtime translations and translation inventory/review artifacts

**Risk note:** this audit did not perform an exhaustive visual sweep of every EN/DE string on every page and every export. It relied on:

- current working tree code review
- existing automated tests
- targeted string/repo searches

No obvious user-facing `TODO` / `FIXME` / debug text leaks were found in the main UI/report/plot code search, but a final manual bilingual UI sweep is still recommended after the blocker is fixed.

## I) Deployment-Einschätzung

### Streamlit Community Cloud
- **Feasibility:** possible for the core app
- **Risk:** medium-high
- **Why:** browser-backed Kaleido export and optional SAV support are the main uncertainties. Community Cloud is less flexible than Docker/VPS for system-level browser/runtime tuning.

### Local portable version
- **Feasibility:** reasonable for an internal/demo Windows audience
- **Risk:** medium
- **Why:** `start_server.bat` helps, but this is not a true packaged desktop distribution; users still need a prepared `.venv` and dependencies.

### Own server / VPS
- **Feasibility:** good
- **Risk:** medium
- **Why:** README documents Linux/VPS setup and nginx proxying. Browser runtime for Kaleido still needs to be provisioned correctly.

### Docker
- **Feasibility:** best current deployment path
- **Risk:** low-medium
- **Why:** Dockerfile installs Chromium and sets `BROWSER_PATH`, which directly addresses the export dependency path.

## J) Empfohlene nächste Schritte

1. **P1 - Create a clean release candidate snapshot**  
   Commit or otherwise freeze the intended release state, remove/reconcile unrelated local modifications, and rerun the audit on that exact snapshot.

2. **P1 - Run one real export smoke test in the target deployment environment**  
   Validate PNG + PPTX output on the intended customer runtime with Chrome/Chromium available.

3. **P2 - Tighten repo hygiene**  
   Ignore local workspace files (for example `*.code-workspace`) and decide whether generated theory/reference artifacts should remain tracked.

4. **P2 - Decide future SAV strategy explicitly**  
   Either keep SAV path-based parsing as a developer-only utility or remove it entirely from the codebase and CI surface.

5. **P3 - Run one final bilingual UI/export pass on the frozen release candidate**  
   Focus on visual fidelity, not logic: DE/EN wording, chart labels, KPI cards, and PPTX viewer rendering.

---

## UI/UX Review Note

Per `AGENTS.md`, a UI review was required. The local `skills/ux-patch-guardian/SKILL.md` checklist was applied manually during this audit. Because this was an audit-only task, no fixes were implemented.

### Findings

- **Critical** - None found in the current audited working tree after the SAV upload fix.
- **Major** - No obvious unfinished labels, debug text leaks, or broken navigation were found through code search and current-state review.
- **Minor** - A final bilingual visual pass is still recommended once the release candidate is frozen, especially for export viewer fidelity and late-stage i18n polish.

### Residual Risks

- No browser-based visual smoke test was run in this audit environment.
- Current UI conclusions are based on code inspection, tests, and repository searches rather than a full live walkthrough on all pages in both languages.
