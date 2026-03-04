# AGENTS.md

## Purpose

This repository is a public, non-client-specific demo for PSM analytics.

## Mandatory guardrails

- Do not commit any real client dataset.
- Keep sensitive local files in `data_private/` only.
- Uploaded files in the Streamlit app must be processed in-memory.
- Do not add external AI/API runtime dependencies.

## UI review policy

- Always apply `skills/ux-patch-guardian` when a task touches UI/UX.
- Trigger scope includes changes under `src/psm_tool/ui/`, `src/psm_tool/plots/`, visual report layout in `src/psm_tool/report/`, and any user-visible copy.
- Before finishing a UI-related task, run the skill checklist and report findings/fixes by severity.

## Testing bar

- Add unit tests for all non-trivial computation functions.
- Keep deterministic regression coverage via synthetic fixtures.
