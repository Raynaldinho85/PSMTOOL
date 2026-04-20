# Streamlit Community Cloud Demo Deploy

This project already contains the pieces needed for a lightweight demo deploy:

- Streamlit entrypoint: `src/psm_tool/ui/app.py`
- Optional password gate: `APP_PASSWORD`
- Demo restrictions: `DEMO_MODE`, `MAX_UPLOAD_MB`, `MAX_ROWS_DEMO`
- Root dependency file for Community Cloud: `requirements.txt`
- Linux package file for Kaleido export browser support: `packages.txt`

## Recommended demo posture

Use Streamlit Community Cloud for presentation and early feedback only.

- Upload only synthetic, anonymized, or clearly non-sensitive data.
- Keep the app private if practical. If you need the fastest sharing flow, use a password.
- Treat this as a demo environment, not the final production hosting model.

## GitHub prep

1. Push this repository to GitHub.
2. Keep `.streamlit/secrets.toml` local only. Do not commit secrets.
3. Confirm the app starts locally before deploy:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src/psm_tool/ui/app.py
```

## Streamlit Community Cloud settings

Create a new app at `share.streamlit.io` and use:

- Repository: your GitHub repo
- Branch: your demo branch or `main`
- Main file path: `src/psm_tool/ui/app.py`
- Python version: `3.11`

Use `Advanced settings` to add secrets. The quickest safe demo baseline is:

```toml
DEMO_MODE = "true"
APP_PASSWORD = "replace-with-demo-password"
MAX_UPLOAD_MB = "10"
MAX_ROWS_DEMO = "2000"
```

These values match the local template in `.streamlit/secrets.example.toml`.

## Why these files were added

- `requirements.txt`
  - Community Cloud recommends a root `requirements.txt`.
  - This file installs the local package via `-e .`, which reuses the existing dependency pins from `pyproject.toml`.
- `packages.txt`
  - PPTX export uses Kaleido v1, which needs Chrome/Chromium.
  - `chromium` is requested as a Debian package for the Linux runtime used by Community Cloud.

## Smoke-test checklist after deploy

1. Open the app URL and verify the password gate appears.
2. Upload the packaged sample data.
3. Open Results and verify charts/KPIs render.
4. Open Export and test both Excel and PPTX downloads.
5. Confirm no raw respondent preview is shown in demo mode.

## Known demo risks

- Community Cloud hosts apps in the United States.
- Free apps have shared resource limits, so large files or heavy exports can be slower.
- Browser-backed export can still fail if the runtime image changes; the export page already includes a preflight check.

## If PPTX export fails in Cloud

Use the app anyway for the live walkthrough and position PPTX export as a follow-up environment check. Excel export and on-screen analysis remain the priority for a first customer demo.
