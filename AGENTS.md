# AGENTS.md

## Purpose

This repository is a public, non-client-specific demo for PSM analytics.

## Mandatory guardrails

- Do not commit any real client dataset.
- Keep sensitive local files in `data_private/` only.
- Uploaded files in the Streamlit app must be processed in-memory.
- Do not add external AI/API runtime dependencies.

## Testing bar

- Add unit tests for all non-trivial computation functions.
- Keep deterministic regression coverage via synthetic fixtures.
